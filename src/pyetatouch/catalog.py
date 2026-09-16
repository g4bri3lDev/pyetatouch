"""Component types and the global, id-keyed variable catalog."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ComponentType(StrEnum):
    """Kind of function block (device metadata only)."""

    BOILER = "boiler"
    HEATING_CIRCUIT = "heating_circuit"
    HOT_WATER = "hot_water"
    PELLET_STORE = "pellet_store"
    SOLAR = "solar"
    SYSTEM = "system"
    BUFFER = "buffer"
    FRESH_WATER = "fresh_water"
    CIRCULATION = "circulation"


class Kind(StrEnum):
    """How a catalog variable behaves."""

    MEASUREMENT = "measurement"  # numeric, read-only
    TOTAL = "total"  # numeric, monotonically increasing counter
    STATE = "state"  # enumerated, read-only
    SETTING = "setting"  # numeric, writable when varinfo says so
    SWITCH = "switch"  # writable, exactly two options (off, on)
    SELECT = "select"  # writable, several options


NEEDS_INFO = frozenset({Kind.STATE, Kind.SETTING, Kind.SWITCH, Kind.SELECT})

Alias = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """A known variable id; aliases are (fkt, io, var) in preference order.

    default_types: None = enabled by default wherever it occurs; otherwise only
    on these component types (an empty set means never enabled by default).
    """

    key: str
    kind: Kind
    aliases: tuple[Alias, ...]
    default_types: frozenset[ComponentType] | None = None


B = ComponentType.BOILER
HC = ComponentType.HEATING_CIRCUIT
HW = ComponentType.HOT_WATER
PS = ComponentType.PELLET_STORE
BU = ComponentType.BUFFER
SO = ComponentType.SOLAR
SY = ComponentType.SYSTEM

# (first fub, last fub, type). Bounds beyond observed ids are provisional.
_FUB_TYPES: tuple[tuple[int, int, ComponentType], ...] = (
    (10021, 10030, B),
    (10101, 10110, HC),
    (10111, 10120, HW),
    (10201, 10220, PS),
    (10221, 10230, SO),
    (10241, 10250, SY),
    (10251, 10260, BU),
    (10391, 10400, B),
    (10531, 10540, ComponentType.FRESH_WATER),
    (10561, 10570, B),
    (10601, 10610, BU),
    (10801, 10810, ComponentType.CIRCULATION),
)

NEVER: frozenset[ComponentType] = frozenset()


def component_type(fub: int) -> ComponentType | None:
    """Return the component type of a fub id, or None if unknown."""
    for first, last, ctype in _FUB_TYPES:
        if first <= fub <= last:
            return ctype
    return None


def _e(
    key: str,
    kind: Kind,
    *aliases: Alias,
    default: frozenset[ComponentType] | None = None,
) -> CatalogEntry:
    return CatalogEntry(key, kind, aliases, default)


M, T, S, N, W, L = (
    Kind.MEASUREMENT,
    Kind.TOTAL,
    Kind.STATE,
    Kind.SETTING,
    Kind.SWITCH,
    Kind.SELECT,
)

CATALOG: tuple[CatalogEntry, ...] = (
    # shared by several component types
    _e("power", W, (0, 0, 12080), default=frozenset({B, HC, HW})),
    _e("outdoor_temperature", M, (0, 0, 12197), (0, 11127, 0), default=frozenset({SY})),
    _e("flow_temperature", M, (0, 11060, 0), (0, 0, 12241), default=frozenset({HC})),
    _e("return_temperature", M, (0, 0, 12220), default=frozenset({HC})),
    _e("hot_water_charge_now", W, (0, 0, 12134), default=frozenset({HW})),
    _e("switch_on_difference", N, (0, 0, 12133), default=NEVER),
    _e("priority", L, (0, 0, 12770), default=NEVER),
    _e("requested_power", M, (0, 0, 12077), default=NEVER),
    # boiler
    _e("boiler_state", S, (0, 0, 19402)),
    _e("boiler_temperature", M, (0, 11109, 0), (0, 0, 12161)),
    _e("boiler_target_temperature", M, (0, 0, 12001)),
    _e("boiler_return_temperature", M, (0, 11160, 0)),
    _e("flue_gas_temperature", M, (0, 11110, 0), (0, 0, 12162)),
    _e("residual_oxygen", M, (0, 0, 12164), (0, 11108, 0)),
    _e("boiler_pressure", M, (0, 0, 12180)),
    _e("requested_temperature", M, (0, 0, 12006), default=NEVER),
    _e("flue_gas_fan_speed", M, (0, 0, 12165), default=NEVER),
    _e("boiler_pump", M, (0, 11123, 0), default=NEVER),
    _e("stoker_screw", M, (0, 11030, 0), default=NEVER),
    _e("ignition", S, (0, 11041, 0), default=NEVER),
    _e("suction_turbine", S, (0, 11042, 0), default=NEVER),
    _e("ash_box", S, (0, 11034, 0), default=NEVER),
    _e("pellet_container", S, (0, 0, 12005)),
    _e("pellet_container_content", M, (0, 0, 12011)),
    _e("total_consumption", T, (0, 0, 12016)),
    _e("consumption_since_ash_box_emptied", T, (0, 0, 12013)),
    _e("consumption_since_deashing", T, (0, 0, 12012), default=NEVER),
    _e("empty_ash_box_after", N, (0, 0, 12120), default=NEVER),
    _e("full_load_hours", T, (0, 0, 12153)),
    _e("full_load_hours_since_service", T, (0, 0, 12404), default=NEVER),
    _e("full_load_hours_since_cleaning", T, (0, 0, 15059), default=NEVER),
    _e("ignition_count", T, (0, 0, 12018), default=NEVER),
    _e("heating_run_count", T, (0, 0, 12017), default=NEVER),
    _e("fill_pellet_container", W, (0, 0, 12071), default=NEVER),
    # pellet store
    _e("discharge_state", S, (0, 0, 19417)),
    _e("pellet_stock", M, (0, 0, 12015)),
    _e("pellet_stock_warning_limit", N, (0, 0, 12042), default=NEVER),
    _e("discharge_screw", M, (0, 11029, 0), default=NEVER),
    # heating circuit
    _e("heating_circuit_state", S, (0, 0, 19404)),
    _e("operating_mode", S, (0, 0, 12092)),
    _e("heating_circuit_pump", S, (0, 11124, 0), default=NEVER),
    _e("curve_offset", N, (0, 0, 12240)),
    _e("flow_at_minus_10", N, (0, 0, 12104), default=NEVER),
    _e("flow_at_plus_10", N, (0, 0, 12103), default=NEVER),
    _e("setback_reduction", N, (0, 0, 12107), default=NEVER),
    _e("heating_limit_day", N, (0, 0, 12096), default=NEVER),
    _e("heating_limit_night", N, (0, 0, 12097), default=NEVER),
    _e("heat_button", W, (0, 0, 12125)),
    _e("auto_button", W, (0, 0, 12126)),
    _e("setback_button", W, (0, 0, 12230)),
    _e("come_button", W, (0, 0, 12218), default=NEVER),
    _e("go_button", W, (0, 0, 12231), default=NEVER),
    # hot water
    _e("hot_water_state", S, (0, 0, 19406)),
    _e("hot_water_temperature", M, (0, 11129, 0), (0, 0, 12271)),
    _e("hot_water_bottom_temperature", M, (0, 0, 12272), default=NEVER),
    _e("hot_water_target_temperature", N, (0, 0, 12132)),
    _e("charge_now_target_temperature", N, (0, 0, 14257), default=NEVER),
    _e("hot_water_charging_pump", S, (0, 11131, 0), default=NEVER),
    # buffer
    _e("buffer_state", S, (0, 0, 19403)),
    _e("buffer_charge_level", M, (0, 0, 12528)),
    _e("buffer_top_temperature", M, (0, 0, 13191), (0, 11327, 0)),
    _e("buffer_bottom_temperature", M, (0, 0, 13192)),
    _e("buffer_sensor_2_temperature", M, (0, 11328, 0), default=NEVER),
    _e("buffer_sensor_3_temperature", M, (0, 11329, 0), default=NEVER),
    _e("buffer_sensor_4_temperature", M, (0, 11330, 0), default=NEVER),
    _e("buffer_top_target_temperature", M, (0, 0, 13194), default=NEVER),
    _e("buffer_charge_now", W, (0, 0, 13025)),
    _e("buffer_charge_count", T, (0, 0, 15044), default=NEVER),
    # solar
    _e("solar_state", S, (0, 0, 19408)),
    _e("collector_temperature", M, (0, 11139, 0), (0, 0, 12275)),
    _e("collector_pump", M, (0, 0, 12278), (0, 11142, 0)),
    _e("storage_1_bottom_temperature", M, (0, 0, 12781), default=NEVER),
    # system
    _e("fault_status", S, (0, 0, 14262), default=NEVER),
)

_BY_ALIAS: dict[Alias, CatalogEntry] = {
    alias: entry for entry in CATALOG for alias in entry.aliases
}
_BY_KEY: dict[str, CatalogEntry] = {entry.key: entry for entry in CATALOG}


def entry_for_alias(alias: Alias) -> CatalogEntry | None:
    """Return the catalog entry a (fkt, io, var) id belongs to."""
    return _BY_ALIAS.get(alias)


def get_entry(key: str) -> CatalogEntry | None:
    """Look up a catalog entry by key."""
    return _BY_KEY.get(key)


def enabled_by_default(entry: CatalogEntry, component: ComponentType | None) -> bool:
    """Whether an entity for this entry should be enabled on this component type."""
    if entry.default_types is None:
        return True
    return component in entry.default_types
