"""Tests for the catalog."""

import pytest

from pyetatouch.catalog import (
    CATALOG,
    ComponentType,
    Kind,
    component_type,
    get_entry,
)
from pyetatouch.parsing import parse_document, parse_menu
from tests.helpers import private_fixture, requires_private


@pytest.mark.parametrize(
    ("fub", "expected"),
    [
        (10021, ComponentType.BOILER),
        (10101, ComponentType.HEATING_CIRCUIT),
        (10102, ComponentType.HEATING_CIRCUIT),
        (10111, ComponentType.HOT_WATER),
        (10201, ComponentType.PELLET_STORE),
        (10221, ComponentType.SOLAR),
        (10241, ComponentType.SYSTEM),
        (10251, ComponentType.BUFFER),
        (10601, ComponentType.BUFFER_FLEX),
        (10531, None),
        (10801, None),
        (99999, None),
    ],
)
def test_component_type(fub: int, expected: ComponentType | None) -> None:
    assert component_type(fub) is expected


def test_every_type_has_a_catalog() -> None:
    assert set(CATALOG) == set(ComponentType)


@pytest.mark.parametrize("ctype", list(ComponentType))
def test_entries_are_consistent(ctype: ComponentType) -> None:
    entries = CATALOG[ctype]
    keys = [entry.key for entry in entries]
    assert len(keys) == len(set(keys)), "duplicate keys"
    aliases = [alias for entry in entries for alias in entry.aliases]
    assert len(aliases) == len(set(aliases)), "alias used by two entries"
    assert all(entry.aliases for entry in entries)


@requires_private
def test_catalog_aliases_exist_on_reference_heater() -> None:
    menu = parse_menu(parse_document(private_fixture("menu.xml"), 200))
    keys_by_type: dict[ComponentType, set[tuple[int, int, int]]] = {}
    for fub in menu:
        ctype = component_type(fub.fub)
        assert ctype is not None
        keys_by_type.setdefault(ctype, set()).update(fub.variables)
    for ctype, keys in keys_by_type.items():
        for entry in CATALOG[ctype]:
            for alias in entry.aliases:
                assert alias in keys, f"{ctype}.{entry.key}: {alias} not in menu"


def test_get_entry() -> None:
    entry = get_entry(ComponentType.HOT_WATER, "target_temperature")
    assert entry is not None
    assert entry.kind is Kind.SETTING
    assert get_entry(ComponentType.HOT_WATER, "nope") is None
