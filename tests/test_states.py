"""Tests for stable state keys."""

import pytest

from pyetatouch.exceptions import EtaValidationError
from pyetatouch.models import VarAddress, VarInfo
from pyetatouch.states import STATE_KEYS, code_for_state, state_key, state_keys

ADDR = VarAddress(120, 10101, 0, 0, 12092)


def _info(options: dict[int, str]) -> VarInfo:
    return VarInfo(ADDR, "Betrieb", "Betrieb", "TEXT", "", 1, True, options=options)


def test_state_key() -> None:
    assert state_key(4001) == "ready"
    assert state_key(3641) == "demand"
    assert state_key(9999) == "code_9999"


def test_keys_are_slugs() -> None:
    assert all(key.replace("_", "").isalnum() and key.islower() for key in STATE_KEYS.values())


def test_state_keys_are_unique_and_ordered() -> None:
    info = _info({2301: "Heizen", 2302: "Absenken", 2303: "Heizen", 2305: "Aus", 4999: "?"})
    assert state_keys(info) == ["heating", "setback", "off", "code_4999"]


def test_code_for_state() -> None:
    info = _info({1971: "Niedrig", 1972: "Mittel", 1973: "Hoch"})
    assert code_for_state(info, "medium") == 1972
    with pytest.raises(EtaValidationError):
        code_for_state(info, "heating")
