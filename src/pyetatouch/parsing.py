"""Parse ETAtouch REST XML documents into models."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime

from .exceptions import EtaNotEtaDeviceError, EtaResponseError, error_for
from .models import EtaFault, MenuFub, VarAddress, VarInfo, VarValue

NS = "{http://www.eta.co.at/rest/v1}"
_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def parse_document(body: bytes | str, status: int) -> ET.Element:
    """Parse a response body and raise for error documents."""
    try:
        root = ET.fromstring(body)
    except ET.ParseError as err:
        raise EtaNotEtaDeviceError(f"HTTP {status}: response is not XML") from err
    if root.tag != f"{NS}eta":
        raise EtaNotEtaDeviceError(f"HTTP {status}: unexpected root element {root.tag!r}")
    error = root.find(f"{NS}error")
    if error is not None:
        raise error_for(status, error.text or "")
    if status >= 400:
        raise EtaResponseError(status, "error response without <error> element")
    return root


def _child(parent: ET.Element, tag: str) -> ET.Element:
    element = parent.find(f"{NS}{tag}")
    if element is None:
        raise EtaNotEtaDeviceError(f"missing <{tag}> element")
    return element


def _instance(uri: str) -> tuple[int, int]:
    parts = [part for part in uri.split("/") if part]
    try:
        return int(parts[0]), int(parts[1])
    except (IndexError, ValueError) as err:
        raise EtaNotEtaDeviceError(f"invalid function block uri {uri!r}") from err


def _int(text: str | None, default: int) -> int:
    return int(text) if text else default


def _float(text: str | None) -> float | None:
    text = (text or "").strip()
    return float(text) if text else None


def parse_api_version(root: ET.Element) -> str:
    """Return the API version string, e.g. '1.2'."""
    return _child(root, "api").get("version", "")


def parse_menu(root: ET.Element) -> list[MenuFub]:
    """Return the top-level function blocks with their deduplicated variables."""
    result: list[MenuFub] = []
    for fub in _child(root, "menu").findall(f"{NS}fub"):
        node, fub_id = _instance(fub.get("uri", ""))
        variables: dict[tuple[int, int, int], str] = {}
        for obj in fub.iter(f"{NS}object"):
            try:
                address = VarAddress.parse(obj.get("uri", ""))
            except ValueError:
                continue
            if address.instance == (node, fub_id):
                variables.setdefault(address.key, obj.get("name", ""))
        result.append(MenuFub(node, fub_id, fub.get("name", ""), variables))
    return result


def _value(element: ET.Element) -> VarValue:
    return VarValue(
        address=VarAddress.parse(element.get("uri", "")),
        raw=float((element.text or "0").strip()),
        text=element.get("strValue", ""),
        unit=element.get("unit", ""),
        scale=_int(element.get("scaleFactor"), 1),
        dec_places=_int(element.get("decPlaces"), 0),
        text_offset=_int(element.get("advTextOffset"), 0),
    )


def parse_value(root: ET.Element) -> VarValue:
    """Parse a /user/var response."""
    return _value(_child(root, "value"))


def parse_varset(root: ET.Element) -> dict[VarAddress, VarValue]:
    """Parse a /user/vars/{name} response."""
    values = (_value(element) for element in _child(root, "vars").findall(f"{NS}variable"))
    return {value.address: value for value in values}


def parse_varinfo(root: ET.Element) -> VarInfo:
    """Parse a /user/varinfo response."""
    variable = _child(_child(root, "varInfo"), "variable")
    minimum = maximum = default = None
    options: dict[int, str] = {}
    valid = variable.find(f"{NS}validValues")
    if valid is not None:
        for element in valid:
            tag = element.tag.removeprefix(NS)
            if tag == "value":
                options[int(float((element.text or "0").strip()))] = element.get("strValue", "")
            elif tag == "min":
                minimum = _float(element.text)
            elif tag == "max":
                maximum = _float(element.text)
            elif tag == "def":
                default = _float(element.text)
    if minimum == 0 and maximum == 0:
        minimum = maximum = None
    type_element = variable.find(f"{NS}type")
    return VarInfo(
        address=VarAddress.parse(variable.get("uri", "")),
        name=variable.get("name", ""),
        full_name=variable.get("fullName", ""),
        type=(type_element.text or "").strip() if type_element is not None else "",
        unit=variable.get("unit", ""),
        scale=_int(variable.get("scaleFactor"), 1),
        writable=variable.get("isWritable") == "1",
        minimum=minimum,
        maximum=maximum,
        default=default,
        options=options,
    )


def _time(text: str | None) -> datetime | None:
    try:
        return datetime.strptime(text or "", _TIME_FORMAT)
    except ValueError:
        return None


def parse_errors(root: ET.Element) -> list[EtaFault]:
    """Parse /user/errors into a flat list of active faults."""
    faults: list[EtaFault] = []
    for fub in _child(root, "errors").findall(f"{NS}fub"):
        node, fub_id = _instance(fub.get("uri", ""))
        for error in fub.findall(f"{NS}error"):
            faults.append(
                EtaFault(
                    node=node,
                    fub=fub_id,
                    fub_name=fub.get("name", ""),
                    message=error.get("msg", ""),
                    priority=error.get("priority", ""),
                    time=_time(error.get("time")),
                    description=(error.text or "").strip(),
                )
            )
    return faults


def parse_success(root: ET.Element) -> None:
    """Ensure the document is a <success> acknowledgement."""
    _child(root, "success")
