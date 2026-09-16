"""Tests for XML parsing."""

from datetime import datetime

import pytest

from pyetatouch.exceptions import (
    EtaNotEtaDeviceError,
    EtaPermissionError,
    EtaResponseError,
)
from pyetatouch.models import VarAddress
from pyetatouch.parsing import (
    parse_api_version,
    parse_document,
    parse_errors,
    parse_menu,
    parse_success,
    parse_value,
    parse_varinfo,
    parse_varset,
)
from tests.helpers import load_fixture, private_fixture, requires_private, varinfo_xml


def test_api_version() -> None:
    root = parse_document(load_fixture("api.xml"), 200)
    assert parse_api_version(root) == "1.2"


def test_menu() -> None:
    menu = parse_menu(parse_document(load_fixture("menu_small.xml"), 200))
    by_name = {fub.name: fub for fub in menu}
    assert list(by_name) == ["HK", "FBH", "WW", "Kessel", "FWM"]
    assert (by_name["HK"].node, by_name["HK"].fub) == (120, 10101)
    assert (by_name["FBH"].node, by_name["FBH"].fub) == (120, 10102)
    assert by_name["HK"].variables.keys() == by_name["FBH"].variables.keys()
    assert len(by_name["HK"].variables) == 5
    # (0, 11109, 0) appears twice in Kessel; the first name wins, no duplicates
    assert by_name["Kessel"].variables[(0, 11109, 0)] == "Kessel"
    assert len(by_name["Kessel"].variables) == 6


@requires_private
def test_menu_reference_heater() -> None:
    menu = parse_menu(parse_document(private_fixture("menu.xml"), 200))
    by_name = {fub.name: fub for fub in menu}
    assert list(by_name) == ["HK", "Solar", "FBH", "Lager", "Sys", "PufferFlex", "WW", "Kessel"]
    assert by_name["HK"].variables.keys() == by_name["FBH"].variables.keys()
    assert len(by_name["HK"].variables) == 117


def test_value() -> None:
    value = parse_value(parse_document(load_fixture("var_boiler_temperature.xml"), 200))
    assert value.address == VarAddress(40, 10021, 0, 11109, 0)
    assert value.raw == 600.0
    assert (value.text, value.unit, value.scale, value.text_offset) == ("60", "°C", 10, 0)


def test_value_with_exponent() -> None:
    value = parse_value(parse_document(load_fixture("var_full_load_hours.xml"), 200))
    assert value.raw == 1.2e7
    assert value.unit == "s"


def test_varinfo_number() -> None:
    info = parse_varinfo(parse_document(load_fixture("varinfo_ww_target.xml"), 200))
    assert info.address == VarAddress(120, 10111, 0, 0, 12132)
    assert info.name == "Warmwasserspeicher Soll"
    assert info.type == "DEFAULT"
    assert info.writable is True
    assert (info.minimum, info.maximum, info.scale, info.unit) == (0.0, 900.0, 10, "°C")
    assert info.options == {}


def test_varinfo_options() -> None:
    info = parse_varinfo(parse_document(load_fixture("varinfo_ww_on_off.xml"), 200))
    assert info.type == "TEXT"
    assert dict(info.options) == {1802: "Aus", 1803: "Ein"}


def test_varinfo_without_limits() -> None:
    info = parse_varinfo(parse_document(load_fixture("varinfo_pellet_content.xml"), 200))
    assert info.writable is True
    assert info.minimum is None
    assert info.maximum is None


def test_varinfo_read_only() -> None:
    info = parse_varinfo(parse_document(load_fixture("varinfo_boiler_temperature.xml"), 200))
    assert info.writable is False
    assert info.full_name == "Eingänge > Kessel"


def test_varinfo_builder_matches_parser() -> None:
    xml = varinfo_xml(
        "120/10101/0/0/12240", "Schieber", writable=True, scale=10, limits=(-1000, 0, 1000)
    )
    info = parse_varinfo(parse_document(xml, 200))
    assert (info.minimum, info.maximum, info.scale) == (-1000.0, 1000.0, 10)


def test_varset() -> None:
    values = parse_varset(parse_document(load_fixture("varset_two.xml"), 200))
    assert values[VarAddress(40, 10021, 0, 11109, 0)].raw == 600.0
    assert values[VarAddress(40, 10021, 0, 11110, 0)].raw == 400.0


def test_varset_empty() -> None:
    assert parse_varset(parse_document(load_fixture("varset_empty.xml"), 200)) == {}


def test_errors_none() -> None:
    assert parse_errors(parse_document(load_fixture("errors_none.xml"), 200)) == []


def test_errors_active() -> None:
    (fault,) = parse_errors(parse_document(load_fixture("errors_active.xml"), 200))
    assert (fault.node, fault.fub, fault.fub_name) == (40, 10021, "Kessel")
    assert fault.message == "Abgasfühler Eingang unterbrochen"
    assert fault.priority == "Error"
    assert fault.time == datetime(2026, 9, 16, 12, 47, 50)
    assert fault.description == "Fühler oder Kabel defekt"


def test_success() -> None:
    parse_success(parse_document(load_fixture("success.xml"), 200))


def test_success_missing() -> None:
    with pytest.raises(EtaNotEtaDeviceError):
        parse_success(parse_document(load_fixture("varset_empty.xml"), 200))


def test_error_document() -> None:
    with pytest.raises(EtaPermissionError) as info:
        parse_document(load_fixture("error_permission.xml"), 400)
    assert info.value.status == 400


@pytest.mark.parametrize(("body", "status"), [(load_fixture("not_eta.html"), 200), ("", 404)])
def test_not_eta(body: str, status: int) -> None:
    with pytest.raises(EtaNotEtaDeviceError):
        parse_document(body, status)


def test_foreign_xml() -> None:
    with pytest.raises(EtaNotEtaDeviceError):
        parse_document("<?xml version='1.0'?><root/>", 200)


def test_error_status_without_error_element() -> None:
    with pytest.raises(EtaResponseError):
        parse_document(load_fixture("success.xml"), 500)
