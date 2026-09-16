"""Transport abstraction shared by the REST variable set and (later) Modbus."""

from __future__ import annotations

from typing import Protocol

from .models import VarAddress, VarValue


class Transport(Protocol):
    """Bulk read and raw write of a fixed set of variables."""

    async def read_all(self) -> dict[VarAddress, VarValue]:
        """Read every variable of the transport."""
        ...

    async def write_raw(self, address: VarAddress, raw: int) -> None:
        """Write a raw value."""
        ...
