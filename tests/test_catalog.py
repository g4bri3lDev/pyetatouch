"""Tests for the global catalog."""

import pytest

from pyetatouch.catalog import (
    CATALOG,
    CatalogEntry,
    ComponentType,
    Kind,
    component_type,
    enabled_by_default,
    entry_for_alias,
    get_entry,
)
from pyetatouch.parsing import parse_document, parse_menu
from tests.helpers import private_fixture, requires_private

B, HC, HW = ComponentType.BOILER, ComponentType.HEATING_CIRCUIT, ComponentType.HOT_WATER


@pytest.mark.parametrize(
    ("fub", "expected"),
    [
        (10021, B),
        (10391, B),
        (10561, B),
        (10101, HC),
        (10102, HC),
        (10111, HW),
        (10201, ComponentType.PELLET_STORE),
        (10211, ComponentType.PELLET_STORE),
        (10221, ComponentType.SOLAR),
        (10241, ComponentType.SYSTEM),
        (10251, ComponentType.BUFFER),
        (10601, ComponentType.BUFFER),
        (10531, ComponentType.FRESH_WATER),
        (10801, ComponentType.CIRCULATION),
        (10999, None),
    ],
)
def test_component_type(fub: int, expected: ComponentType | None) -> None:
    assert component_type(fub) is expected


def test_keys_and_aliases_are_unique() -> None:
    keys = [entry.key for entry in CATALOG]
    assert len(keys) == len(set(keys))
    aliases = [alias for entry in CATALOG for alias in entry.aliases]
    assert len(aliases) == len(set(aliases))
    assert all(entry.aliases for entry in CATALOG)


def test_lookup() -> None:
    power = entry_for_alias((0, 0, 12080))
    assert power is not None and power.key == "power" and power.kind is Kind.SWITCH
    assert entry_for_alias((0, 11109, 0)) is entry_for_alias((0, 0, 12161))
    assert entry_for_alias((9, 9, 9)) is None
    assert get_entry("outdoor_temperature") is entry_for_alias((0, 0, 12197))
    assert get_entry("nope") is None


def test_enabled_by_default() -> None:
    def entry(key: str) -> CatalogEntry:
        found = get_entry(key)
        assert found is not None
        return found

    assert enabled_by_default(entry("power"), HC)
    assert not enabled_by_default(entry("power"), ComponentType.BUFFER)
    assert enabled_by_default(entry("outdoor_temperature"), ComponentType.SYSTEM)
    assert not enabled_by_default(entry("outdoor_temperature"), HC)
    assert not enabled_by_default(entry("outdoor_temperature"), None)
    assert enabled_by_default(entry("boiler_temperature"), None)
    assert not enabled_by_default(entry("priority"), HW)


@requires_private
def test_aliases_exist_on_reference_heater() -> None:
    menu = parse_menu(parse_document(private_fixture("menu.xml"), 200))
    ids = {key for fub in menu for key in fub.variables}
    missing = [(e.key, a) for e in CATALOG for a in e.aliases if a not in ids]
    assert missing == []


def test_mode_and_action_kinds() -> None:
    for key in ("heat_button", "auto_button", "setback_button"):
        entry = get_entry(key)
        assert entry is not None and entry.kind is Kind.MODE
    for key in ("come_button", "go_button", "fill_pellet_container"):
        entry = get_entry(key)
        assert entry is not None and entry.kind is Kind.ACTION


def test_time_kind() -> None:
    for key in ("pellet_suction_time", "quiet_time_start", "anti_seize_time"):
        entry = get_entry(key)
        assert entry is not None and entry.kind is Kind.TIME
