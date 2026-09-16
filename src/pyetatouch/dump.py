"""Anonymised structure report used for catalog requests."""

from __future__ import annotations

from collections.abc import Callable
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from .catalog import component_type, entry_for_alias
from .client import EtaClient
from .exceptions import EtaResponseError
from .models import VarAddress

FORMAT_VERSION = 1


def _library_version() -> str:
    try:
        return version("pyetatouch")
    except PackageNotFoundError:
        return "unknown"


async def _info(client: EtaClient, address: VarAddress) -> dict[str, Any]:
    try:
        info = await client.var_info(address)
    except EtaResponseError as err:
        return {"error": err.message}
    return {
        "type": info.type,
        "unit": info.unit,
        "scale": info.scale,
        "writable": info.writable,
        "minimum": info.minimum,
        "maximum": info.maximum,
        "default": info.default,
        "options": {str(code): label for code, label in info.options.items()},
    }


async def describe(
    client: EtaClient,
    *,
    with_info: bool = True,
    keep_names: bool = False,
    progress: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    """Describe the heater's structure without values or node addresses."""
    api = await client.api_version()
    menu = await client.menu()
    total = sum(len(fub.variables) for fub in menu) if with_info else 0
    done = 0
    counters: dict[str, int] = {}
    components: list[dict[str, Any]] = []
    for fub in menu:
        ctype = component_type(fub.fub)
        label = ctype.value if ctype else "component"
        counters[label] = counters.get(label, 0) + 1
        variables: list[dict[str, Any]] = []
        for key, name in fub.variables.items():
            entry = entry_for_alias(key)
            item: dict[str, Any] = {
                "id": "/".join(str(part) for part in key),
                "name": name,
                "catalog": entry.key if entry else None,
            }
            if with_info:
                item.update(await _info(client, VarAddress(fub.node, fub.fub, *key)))
                done += 1
                if progress is not None:
                    progress(done, total)
            variables.append(item)
        components.append(
            {
                "fub": fub.fub,
                "type": ctype.value if ctype else None,
                "name": fub.name if keep_names else f"{label} {counters[label]}",
                "variables": variables,
            }
        )
    return {
        "format": FORMAT_VERSION,
        "pyetatouch": _library_version(),
        "api": api,
        "components": components,
    }
