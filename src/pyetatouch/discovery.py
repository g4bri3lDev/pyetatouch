"""Find the catalog variables available on a heater."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .catalog import CATALOG, NEEDS_INFO, CatalogEntry, ComponentType, Kind, component_type
from .client import EtaClient
from .models import VarAddress, VarInfo

_LOGGER = logging.getLogger(__name__)
SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class Component:
    """A known function block instance."""

    type: ComponentType
    node: int
    fub: int
    name: str

    @property
    def instance(self) -> tuple[int, int]:
        return (self.node, self.fub)


@dataclass(frozen=True, slots=True)
class UnknownComponent:
    """A function block whose type the catalog does not know."""

    node: int
    fub: int
    name: str


@dataclass(frozen=True, slots=True)
class MatchedVariable:
    """A catalog entry resolved to a readable address."""

    key: str
    address: VarAddress
    info: VarInfo | None


@dataclass(frozen=True, slots=True)
class UnknownVariable:
    """A menu variable that is not in the catalog."""

    address: VarAddress
    name: str


@dataclass(frozen=True, slots=True)
class Installation:
    """Discovery result."""

    components: tuple[Component, ...]
    variables: tuple[MatchedVariable, ...]
    unknown_components: tuple[UnknownComponent, ...] = ()
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
                {"type": c.type.value, "node": c.node, "fub": c.fub, "name": c.name}
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
            "unknown_components": [
                {"node": u.node, "fub": u.fub, "name": u.name} for u in self.unknown_components
            ],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Installation:
        """Restore from to_dict() output."""
        return cls(
            components=tuple(
                Component(ComponentType(c["type"]), c["node"], c["fub"], c["name"])
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
            unknown_components=tuple(
                UnknownComponent(u["node"], u["fub"], u["name"])
                for u in data.get("unknown_components", [])
            ),
        )


async def discover(client: EtaClient, *, set_name: str = "pyetatouchdisc") -> Installation:
    """Match the heater's menu against the catalog and keep readable variables."""
    menu = await client.menu()
    components: list[Component] = []
    unknown_components: list[UnknownComponent] = []
    unknown_variables: list[UnknownVariable] = []
    candidates: list[tuple[CatalogEntry, list[VarAddress]]] = []

    for fub in menu:
        ctype = component_type(fub.fub)
        if ctype is None:
            unknown_components.append(UnknownComponent(fub.node, fub.fub, fub.name))
            continue
        components.append(Component(ctype, fub.node, fub.fub, fub.name))
        claimed: set[tuple[int, int, int]] = set()
        for entry in CATALOG[ctype]:
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
        readable = set(probe.accepted)

    chosen: list[tuple[CatalogEntry, VarAddress]] = []
    for entry, addresses in candidates:
        address = next((a for a in addresses if a in readable), None)
        if address is not None:
            chosen.append((entry, address))

    async def _info(entry: CatalogEntry, address: VarAddress) -> VarInfo | None:
        return await client.var_info(address) if entry.kind in NEEDS_INFO else None

    infos = await asyncio.gather(*(_info(entry, address) for entry, address in chosen))

    variables: list[MatchedVariable] = []
    for (entry, address), info in zip(chosen, infos, strict=True):
        if entry.kind is Kind.SWITCH and (info is None or len(info.options) != 2):
            _LOGGER.debug("Skipping %s at %s: not a two-option variable", entry.key, address)
            continue
        variables.append(MatchedVariable(entry.key, address, info))

    return Installation(
        tuple(components),
        tuple(variables),
        tuple(unknown_components),
        tuple(unknown_variables),
    )
