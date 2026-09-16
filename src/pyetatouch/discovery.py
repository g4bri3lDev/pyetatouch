"""Find the catalog variables available on a heater."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .catalog import (
    CATALOG,
    NEEDS_INFO,
    TWO_OPTION_KINDS,
    CatalogEntry,
    ComponentType,
    component_type,
)
from .client import EtaClient
from .models import VarAddress, VarInfo, VarValue

_LOGGER = logging.getLogger(__name__)
SCHEMA_VERSION = 2
NOT_CONNECTED = "xxx"


def _not_connected(value: VarValue) -> bool:
    """Whether a numeric variable reports that no sensor/function is connected.

    `xxx` marks unconnected inputs; `---` only means "no value right now" and is kept.
    Text variables are kept because their strValue is unreliable.
    """
    return value.text_offset == 0 and value.text.strip() == NOT_CONNECTED


@dataclass(frozen=True, slots=True)
class Component:
    """A function block instance; type is None when the fub id is unknown."""

    type: ComponentType | None
    node: int
    fub: int
    name: str

    @property
    def instance(self) -> tuple[int, int]:
        return (self.node, self.fub)


@dataclass(frozen=True, slots=True)
class MatchedVariable:
    """A catalog entry resolved to a readable address."""

    key: str
    address: VarAddress
    info: VarInfo | None


@dataclass(frozen=True, slots=True)
class UnknownVariable:
    """A menu variable whose id is not in the catalog."""

    address: VarAddress
    name: str


@dataclass(frozen=True, slots=True)
class Installation:
    """Discovery result."""

    components: tuple[Component, ...]
    variables: tuple[MatchedVariable, ...]
    unknown_variables: tuple[UnknownVariable, ...] = ()

    def component_for(self, address: VarAddress) -> Component | None:
        return next((c for c in self.components if c.instance == address.instance), None)

    def variables_for(self, component: Component) -> list[MatchedVariable]:
        return [v for v in self.variables if v.address.instance == component.instance]

    def to_dict(self) -> dict[str, Any]:
        """Serialise to JSON-compatible data (without unknown variables)."""
        return {
            "version": SCHEMA_VERSION,
            "components": [
                {
                    "type": c.type.value if c.type else None,
                    "node": c.node,
                    "fub": c.fub,
                    "name": c.name,
                }
                for c in self.components
            ],
            "variables": [
                {
                    "key": v.key,
                    "address": str(v.address),
                    "info": v.info.to_dict() if v.info else None,
                }
                for v in self.variables
            ],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Installation:
        """Restore from to_dict() output."""
        return cls(
            components=tuple(
                Component(
                    ComponentType(c["type"]) if c["type"] else None,
                    c["node"],
                    c["fub"],
                    c["name"],
                )
                for c in data["components"]
            ),
            variables=tuple(
                MatchedVariable(
                    v["key"],
                    VarAddress.parse(v["address"]),
                    VarInfo.from_dict(v["info"]) if v["info"] else None,
                )
                for v in data["variables"]
            ),
        )


def _keep_one_per_installation(
    chosen: list[tuple[CatalogEntry, VarAddress]], components: list[Component]
) -> list[tuple[CatalogEntry, VarAddress]]:
    """Keep a single occurrence of installation-wide entries.

    Preference: a component whose type enables the entry by default (e.g. the
    system block for the outdoor temperature), otherwise the first in menu order.
    """
    types = {component.instance: component.type for component in components}
    keep: dict[str, VarAddress] = {}
    for entry, address in chosen:
        if not entry.single:
            continue
        current = keep.get(entry.key)
        if current is None or (
            _is_preferred(entry, address, types) and not _is_preferred(entry, current, types)
        ):
            keep[entry.key] = address
    return [
        (entry, address)
        for entry, address in chosen
        if not entry.single or keep[entry.key] == address
    ]


def _is_preferred(
    entry: CatalogEntry,
    address: VarAddress,
    types: dict[tuple[int, int], ComponentType | None],
) -> bool:
    return entry.default_types is not None and types[address.instance] in entry.default_types


async def discover(client: EtaClient, *, set_name: str = "pyetatouchdisc") -> Installation:
    """Match every function block against the catalog and keep readable variables."""
    menu = await client.menu()
    components: list[Component] = []
    unknown_variables: list[UnknownVariable] = []
    candidates: list[tuple[CatalogEntry, list[VarAddress]]] = []

    for fub in menu:
        components.append(Component(component_type(fub.fub), fub.node, fub.fub, fub.name))
        claimed: set[tuple[int, int, int]] = set()
        for entry in CATALOG:
            present = [
                VarAddress(fub.node, fub.fub, *alias)
                for alias in entry.aliases
                if alias in fub.variables
            ]
            if present:
                candidates.append((entry, present))
                claimed.update(entry.aliases)
        unknown_variables.extend(
            UnknownVariable(VarAddress(fub.node, fub.fub, *key), name)
            for key, name in fub.variables.items()
            if key not in claimed
        )

    probe_addresses = [address for _, addresses in candidates for address in addresses]
    async with client.varset(set_name, probe_addresses) as probe:
        values = await probe.read_all() if probe.accepted else {}
    usable = {address for address, value in values.items() if not _not_connected(value)}

    chosen: list[tuple[CatalogEntry, VarAddress]] = []
    for entry, addresses in candidates:
        address = next((a for a in addresses if a in usable), None)
        if address is not None:
            chosen.append((entry, address))
    chosen = _keep_one_per_installation(chosen, components)

    async def _info(entry: CatalogEntry, address: VarAddress) -> VarInfo | None:
        return await client.var_info(address) if entry.kind in NEEDS_INFO else None

    infos = await asyncio.gather(*(_info(entry, address) for entry, address in chosen))

    variables: list[MatchedVariable] = []
    for (entry, address), info in zip(chosen, infos, strict=True):
        if entry.kind in TWO_OPTION_KINDS and (info is None or len(info.options) != 2):
            _LOGGER.debug("Skipping %s at %s: not a two-option variable", entry.key, address)
            continue
        variables.append(MatchedVariable(entry.key, address, info))

    return Installation(tuple(components), tuple(variables), tuple(unknown_variables))
