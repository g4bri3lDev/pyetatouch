"""Tests for models and value conversion."""

import pytest

from pyetatouch.exceptions import EtaValidationError
from pyetatouch.models import (
    VarAddress,
    VarInfo,
    VarValue,
    decode_value,
    encode_value,
    switch_codes,
)

ADDR = VarAddress(120, 10111, 0, 0, 12133)


def _value(raw: float, text: str, *, scale: int = 10, offset: int = 0) -> VarValue:
    return VarValue(ADDR, raw, text, "°C", scale, 0, offset)


def _info(
    *,
    writable: bool = True,
    scale: int = 10,
    minimum: float | None = 0.0,
    maximum: float | None = 300.0,
    options: dict[int, str] | None = None,
) -> VarInfo:
    return VarInfo(
        address=ADDR,
        name="Einschaltdifferenz",
        full_name="Warmwasserspeicher > Einschaltdifferenz",
        type="TEXT" if options else "DEFAULT",
        unit="" if options else "°C",
        scale=scale,
        writable=writable,
        minimum=minimum,
        maximum=maximum,
        default=None,
        options=options or {},
    )


ON_OFF = {1802: "Aus", 1803: "Ein"}


@pytest.mark.parametrize(
    "uri",
    [
        "40/10021/0/11109/0",
        "/40/10021/0/11109/0",
        "/user/var/40/10021/0/11109/0",
        "/user/vars/haspike/40/10021/0/11109/0",
    ],
)
def test_address_parse(uri: str) -> None:
    assert VarAddress.parse(uri) == VarAddress(40, 10021, 0, 11109, 0)


@pytest.mark.parametrize("uri", ["/120/10101", "", "/user/var/a/b/c/d/e"])
def test_address_parse_rejects(uri: str) -> None:
    with pytest.raises(ValueError):
        VarAddress.parse(uri)


def test_address_properties() -> None:
    addr = VarAddress(40, 10021, 0, 11109, 0)
    assert str(addr) == "40/10021/0/11109/0"
    assert addr.key == (0, 11109, 0)
    assert addr.instance == (40, 10021)
    assert {addr: 1}[VarAddress.parse(str(addr))] == 1


def test_decode_numeric() -> None:
    assert decode_value(_value(233.0, "23,3")) == 23.3


def test_decode_large_float() -> None:
    assert decode_value(_value(1.19169e7, "3310h 15m", scale=1)) == 11916900.0


@pytest.mark.parametrize("text", ["xxx", "---", " xxx "])
def test_decode_unavailable(text: str) -> None:
    assert decode_value(_value(0.0, text)) is None


def test_decode_text_without_info() -> None:
    assert decode_value(_value(4001.0, "Bereit", scale=1, offset=4000)) == "Bereit"


def test_decode_text_without_info_unavailable() -> None:
    assert decode_value(_value(1803.0, "xxx", scale=1, offset=1802)) is None


def test_decode_text_prefers_info_labels() -> None:
    info = _info(options={1971: "Niedrig", 1972: "Mittel", 1973: "Hoch"})
    assert decode_value(_value(1973.0, "xxx", scale=1, offset=1971), info) == "Hoch"


def test_decode_text_unknown_code() -> None:
    assert decode_value(_value(1999.0, "?", scale=1, offset=1802), _info(options=ON_OFF)) is None


def test_decode_zero_scale() -> None:
    assert decode_value(_value(5.0, "5", scale=0)) == 5.0


def test_encode_scaled_number() -> None:
    assert encode_value(_info(), 8) == 80
    assert encode_value(_info(), 7.5) == 75


def test_encode_out_of_range() -> None:
    with pytest.raises(EtaValidationError):
        encode_value(_info(), 95)
    with pytest.raises(EtaValidationError):
        encode_value(_info(), -1)


def test_encode_without_limits() -> None:
    assert encode_value(_info(minimum=None, maximum=None), 100000) == 1000000


def test_encode_read_only() -> None:
    with pytest.raises(EtaValidationError):
        encode_value(_info(writable=False), 8)


def test_encode_option_by_label_and_code() -> None:
    info = _info(options=ON_OFF, scale=1)
    assert encode_value(info, "Ein") == 1803
    assert encode_value(info, 1802) == 1802


@pytest.mark.parametrize("value", ["An", 1804])
def test_encode_invalid_option(value: str | int) -> None:
    with pytest.raises(EtaValidationError):
        encode_value(_info(options=ON_OFF, scale=1), value)


def test_encode_text_for_number() -> None:
    with pytest.raises(EtaValidationError):
        encode_value(_info(), "8")


def test_switch_codes() -> None:
    assert switch_codes(_info(options={1803: "Ein", 1802: "Aus"})) == (1802, 1803)


def test_switch_codes_requires_two_options() -> None:
    with pytest.raises(EtaValidationError):
        switch_codes(_info(options={1971: "a", 1972: "b", 1973: "c"}))


def test_varinfo_round_trip() -> None:
    info = _info(options=ON_OFF, scale=1)
    assert VarInfo.from_dict(info.to_dict()) == info
