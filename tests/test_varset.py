"""Tests for VarSet using an in-memory backend."""

import pytest

from pyetatouch.exceptions import (
    EtaConflictError,
    EtaNotFoundError,
    EtaPermissionError,
)
from pyetatouch.models import VarAddress, VarValue
from pyetatouch.transport import Transport
from pyetatouch.varset import VarSet

A = VarAddress(40, 10021, 0, 11109, 0)
B = VarAddress(40, 10021, 0, 11110, 0)
C = VarAddress(120, 10101, 0, 0, 12090)


def _value(address: VarAddress) -> VarValue:
    return VarValue(address, 500.0, "50", "°C", 10, 0, 0)


class FakeBackend:
    """Mimics the heater's variable-set behaviour."""

    def __init__(self, restricted: frozenset[VarAddress] = frozenset()) -> None:
        self.sets: dict[str, list[VarAddress]] = {}
        self.restricted = restricted
        self.calls: list[str] = []
        self.writes: list[tuple[VarAddress, int]] = []
        self.always_missing = False

    async def create_varset(self, name: str) -> None:
        self.calls.append("create")
        if name in self.sets:
            raise EtaConflictError(400, "Variable set already exists")
        self.sets[name] = []

    async def delete_varset(self, name: str) -> None:
        self.calls.append("delete")
        if name not in self.sets:
            raise EtaNotFoundError(404, "Variable set not available")
        del self.sets[name]

    async def add_to_varset(self, name: str, address: VarAddress) -> None:
        if address in self.restricted:
            raise EtaPermissionError(400, "Invalid permission")
        if address in self.sets[name]:
            raise EtaConflictError(400, "Can not add the variable to the variable set")
        self.sets[name].append(address)

    async def read_varset(self, name: str) -> dict[VarAddress, VarValue]:
        self.calls.append("read")
        if self.always_missing or name not in self.sets:
            raise EtaNotFoundError(404, "Variable set not available")
        return {address: _value(address) for address in self.sets[name]}

    async def write_raw(self, address: VarAddress, raw: int) -> None:
        self.writes.append((address, raw))


async def test_create_replaces_leftover() -> None:
    backend = FakeBackend()
    backend.sets["ha1"] = [C]
    varset = VarSet(backend, "ha1", [A, B])
    await varset.create()
    assert sorted(backend.sets["ha1"]) == [A, B]
    assert backend.calls[:2] == ["delete", "create"]


async def test_create_fresh_and_dedupe() -> None:
    backend = FakeBackend()
    varset = VarSet(backend, "ha1", [A, A, B])
    await varset.create()
    assert sorted(varset.accepted) == [A, B]
    assert varset.rejected == ()


async def test_restricted_addresses_are_rejected() -> None:
    backend = FakeBackend(restricted=frozenset({C}))
    varset = VarSet(backend, "ha1", [A, C])
    await varset.create()
    assert varset.accepted == (A,)
    assert varset.rejected == (C,)


async def test_read_all() -> None:
    backend = FakeBackend()
    varset = VarSet(backend, "ha1", [A, B])
    await varset.create()
    assert set(await varset.read_all()) == {A, B}


async def test_read_all_recreates_after_reboot() -> None:
    backend = FakeBackend()
    varset = VarSet(backend, "ha1", [A])
    await varset.create()
    backend.sets.clear()
    assert set(await varset.read_all()) == {A}
    assert backend.calls.count("create") == 2


async def test_read_all_recreates_when_tampered() -> None:
    backend = FakeBackend()
    varset = VarSet(backend, "ha1", [A])
    await varset.create()
    backend.sets["ha1"].append(B)
    assert set(await varset.read_all()) == {A}
    assert backend.sets["ha1"] == [A]


async def test_read_all_second_failure_propagates() -> None:
    backend = FakeBackend()
    varset = VarSet(backend, "ha1", [A])
    await varset.create()
    backend.always_missing = True
    with pytest.raises(EtaNotFoundError):
        await varset.read_all()


async def test_context_manager_deletes() -> None:
    backend = FakeBackend()
    async with VarSet(backend, "ha1", [A]) as varset:
        assert "ha1" in backend.sets
        assert varset.accepted == (A,)
    assert "ha1" not in backend.sets


async def test_delete_tolerates_missing() -> None:
    await VarSet(FakeBackend(), "ha1", [A]).delete()


@pytest.mark.parametrize("name", ["", "ha-1", "ha 1", "a" * 33])
def test_invalid_name(name: str) -> None:
    with pytest.raises(ValueError):
        VarSet(FakeBackend(), name, [A])


async def test_is_a_transport() -> None:
    backend = FakeBackend()
    transport: Transport = VarSet(backend, "ha1", [A])
    await transport.write_raw(A, 70)
    assert backend.writes == [(A, 70)]
