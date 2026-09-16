"""Data models for the ETAtouch REST API and value conversion."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .exceptions import EtaValidationError

UNAVAILABLE_TEXTS = frozenset({"xxx", "---"})


@dataclass(frozen=True, slots=True, order=True)
class VarAddress:
    """Address of an ETAtouch variable: node/fub/fkt/io/var."""

    node: int
    fub: int
    fkt: int
    io: int
    var: int

    @classmethod
    def parse(cls, uri: str) -> VarAddress:
        """Parse an address from any URI ending in the five address segments."""
        parts = [part for part in uri.strip().split("/") if part]
        if len(parts) < 5:
            raise ValueError(f"Not a variable address: {uri!r}")
        try:
            node, fub, fkt, io, var = (int(part) for part in parts[-5:])
        except ValueError as err:
            raise ValueError(f"Not a variable address: {uri!r}") from err
        return cls(node, fub, fkt, io, var)

    def __str__(self) -> str:
        return f"{self.node}/{self.fub}/{self.fkt}/{self.io}/{self.var}"

    @property
    def key(self) -> tuple[int, int, int]:
        """What the variable is (identical for every instance of a component type)."""
        return (self.fkt, self.io, self.var)

    @property
    def instance(self) -> tuple[int, int]:
        """Which component instance the variable belongs to."""
        return (self.node, self.fub)


@dataclass(frozen=True, slots=True)
class VarValue:
    """A value as returned by /user/var or a variable set."""

    address: VarAddress
    raw: float
    text: str
    unit: str
    scale: int
    dec_places: int
    text_offset: int


@dataclass(frozen=True, slots=True)
class VarInfo:
    """Metadata from /user/varinfo. Limits are raw (unscaled) values."""

    address: VarAddress
    name: str
    full_name: str
    type: str
    unit: str
    scale: int
    writable: bool
    minimum: float | None = None
    maximum: float | None = None
    default: float | None = None
    options: Mapping[int, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to JSON-compatible data."""
        return {
            "address": str(self.address),
            "name": self.name,
            "full_name": self.full_name,
            "type": self.type,
            "unit": self.unit,
            "scale": self.scale,
            "writable": self.writable,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "default": self.default,
            "options": {str(code): label for code, label in self.options.items()},
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> VarInfo:
        """Restore from to_dict() output."""
        return cls(
            address=VarAddress.parse(data["address"]),
            name=data["name"],
            full_name=data["full_name"],
            type=data["type"],
            unit=data["unit"],
            scale=data["scale"],
            writable=data["writable"],
            minimum=data["minimum"],
            maximum=data["maximum"],
            default=data["default"],
            options={int(code): label for code, label in data["options"].items()},
        )


@dataclass(frozen=True, slots=True)
class MenuFub:
    """A top-level function block from /user/menu."""

    node: int
    fub: int
    name: str
    variables: Mapping[tuple[int, int, int], str]


@dataclass(frozen=True, slots=True)
class EtaFault:
    """An active error from /user/errors."""

    node: int
    fub: int
    fub_name: str
    message: str
    priority: str
    time: datetime | None
    description: str


def decode_value(value: VarValue, info: VarInfo | None = None) -> float | str | None:
    """Return the user-facing value, or None if the heater reports no value."""
    if info is not None and info.options:
        return info.options.get(int(value.raw))
    if value.text.strip() in UNAVAILABLE_TEXTS:
        return None
    if value.text_offset:
        return value.text
    return value.raw / value.scale if value.scale else value.raw


def encode_value(info: VarInfo, value: float | str) -> int:
    """Convert a user-facing value to the raw integer the heater expects."""
    if not info.writable:
        raise EtaValidationError(f"{info.address} ({info.name}) is read-only")
    if info.options:
        if isinstance(value, str):
            for code, label in info.options.items():
                if label == value:
                    return code
            raise EtaValidationError(f"{value!r} is not an option of {info.name}")
        code = int(value)
        if code not in info.options:
            raise EtaValidationError(f"{code} is not an option code of {info.name}")
        return code
    if isinstance(value, str):
        raise EtaValidationError(f"{info.name} needs a number, got {value!r}")
    raw = round(value * info.scale)
    if (info.minimum is not None and raw < info.minimum) or (
        info.maximum is not None and raw > info.maximum
    ):
        raise EtaValidationError(f"{value} is outside the allowed range of {info.name}")
    return raw


def switch_codes(info: VarInfo) -> tuple[int, int]:
    """Return (off, on) raw codes of a two-option variable."""
    if len(info.options) != 2:
        raise EtaValidationError(f"{info.name} does not have exactly two options")
    off, on = sorted(info.options)
    return off, on
