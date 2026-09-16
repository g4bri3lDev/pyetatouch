"""Self-healing ETAtouch variable sets."""

from __future__ import annotations

import asyncio
import contextlib
import re
from collections.abc import Iterable
from types import TracebackType
from typing import Protocol, Self

from .exceptions import EtaNotFoundError, EtaPermissionError
from .models import VarAddress, VarValue

_NAME = re.compile(r"[A-Za-z0-9]{1,32}")


class VarSetBackend(Protocol):
    """The client operations a VarSet needs."""

    async def create_varset(self, name: str) -> None: ...
    async def delete_varset(self, name: str) -> None: ...
    async def add_to_varset(self, name: str, address: VarAddress) -> None: ...
    async def read_varset(self, name: str) -> dict[VarAddress, VarValue]: ...
    async def write_raw(self, address: VarAddress, raw: int) -> None: ...


class VarSet:
    """A named variable set on the heater, recreated whenever it goes missing."""

    def __init__(self, backend: VarSetBackend, name: str, addresses: Iterable[VarAddress]) -> None:
        if not _NAME.fullmatch(name):
            raise ValueError(f"Invalid variable set name {name!r}")
        self._backend = backend
        self.name = name
        self._requested = tuple(dict.fromkeys(addresses))
        self.accepted: tuple[VarAddress, ...] = ()
        self.rejected: tuple[VarAddress, ...] = ()

    async def _add(self, address: VarAddress) -> bool:
        try:
            await self._backend.add_to_varset(self.name, address)
        except EtaPermissionError:
            return False
        return True

    async def create(self) -> None:
        """(Re)create the set; addresses without permission end up in `rejected`."""
        await self.delete()
        await self._backend.create_varset(self.name)
        results = await asyncio.gather(*(self._add(address) for address in self._requested))
        self.accepted = tuple(a for a, ok in zip(self._requested, results, strict=True) if ok)
        self.rejected = tuple(a for a, ok in zip(self._requested, results, strict=True) if not ok)

    async def read_all(self) -> dict[VarAddress, VarValue]:
        """Read all accepted variables, recreating the set once if needed."""
        try:
            values = await self._backend.read_varset(self.name)
        except EtaNotFoundError:
            values = None
        if values is None or values.keys() != set(self.accepted):
            await self.create()
            values = await self._backend.read_varset(self.name)
        return values

    async def write_raw(self, address: VarAddress, raw: int) -> None:
        """Write a raw value through the backend."""
        await self._backend.write_raw(address, raw)

    async def delete(self) -> None:
        """Delete the set; a missing set is fine."""
        with contextlib.suppress(EtaNotFoundError):
            await self._backend.delete_varset(self.name)

    async def __aenter__(self) -> Self:
        await self.create()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.delete()
