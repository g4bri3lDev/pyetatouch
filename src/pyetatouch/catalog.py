"""Component types and the curated variable catalog."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum


class ComponentType(StrEnum):
    """Kind of function block, derived from the fub id."""

    BOILER = "boiler"
    HEATING_CIRCUIT = "heating_circuit"
    HOT_WATER = "hot_water"
    PELLET_STORE = "pellet_store"
    SOLAR = "solar"
    SYSTEM = "system"
    BUFFER = "buffer"
    BUFFER_FLEX = "buffer_flex"


class Kind(StrEnum):
    """How a catalog variable behaves."""

    MEASUREMENT = "measurement"  # numeric, read-only
    TOTAL = "total"  # numeric, monotonically increasing counter
    STATE = "state"  # enumerated, read-only
    SETTING = "setting"  # numeric, writable when varinfo says so
    SWITCH = "switch"  # writable, exactly two options (off, on)
    SELECT = "select"  # writable, several options


NEEDS_INFO = frozenset({Kind.STATE, Kind.SETTING, Kind.SWITCH, Kind.SELECT})


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """A known variable; aliases are (fkt, io, var) in preference order."""

    key: str
    kind: Kind
    aliases: tuple[tuple[int, int, int], ...]
    enabled_by_default: bool = True


# (first fub, last fub) -> type. Bounds beyond observed ids are provisional.
_FUB_RANGES: tuple[tuple[int, int, ComponentType], ...] = (
    (10021, 10030, ComponentType.BOILER),
    (10101, 10110, ComponentType.HEATING_CIRCUIT),
    (10111, 10120, ComponentType.HOT_WATER),
    (10201, 10210, ComponentType.PELLET_STORE),
    (10221, 10230, ComponentType.SOLAR),
    (10241, 10250, ComponentType.SYSTEM),
    (10251, 10260, ComponentType.BUFFER),
    (10601, 10610, ComponentType.BUFFER_FLEX),
)


def component_type(fub: int) -> ComponentType | None:
    """Return the component type of a fub id, or None if unknown."""
    for first, last, ctype in _FUB_RANGES:
        if first <= fub <= last:
            return ctype
    return None


def _e(key: str, kind: Kind, *aliases: tuple[int, int, int], enabled: bool = True) -> CatalogEntry:
    return CatalogEntry(key, kind, aliases, enabled)


M, T, S, N, W, L = (
    Kind.MEASUREMENT,
    Kind.TOTAL,
    Kind.STATE,
    Kind.SETTING,
    Kind.SWITCH,
    Kind.SELECT,
)

CATALOG: Mapping[ComponentType, tuple[CatalogEntry, ...]] = {
    ComponentType.BOILER: (
        _e("state", S, (0, 0, 19402)),
        _e("temperature", M, (0, 11109, 0), (0, 0, 12161)),
        _e("target_temperature", M, (0, 0, 12001)),
        _e("return_temperature", M, (0, 11160, 0)),
        _e("flue_gas_temperature", M, (0, 11110, 0), (0, 0, 12162)),
        _e("residual_oxygen", M, (0, 0, 12164), (0, 11108, 0)),
        _e("pressure", M, (0, 0, 12180)),
        _e("requested_power", M, (0, 0, 12077), enabled=False),
        _e("requested_temperature", M, (0, 0, 12006), enabled=False),
        _e("flue_gas_fan_speed", M, (0, 0, 12165), enabled=False),
        _e("boiler_pump", M, (0, 11123, 0), enabled=False),
        _e("stoker_screw", M, (0, 11030, 0), enabled=False),
        _e("ignition", S, (0, 11041, 0), enabled=False),
        _e("suction_turbine", S, (0, 11042, 0), enabled=False),
        _e("ash_box", S, (0, 11034, 0), enabled=False),
        _e("pellet_container", S, (0, 0, 12005)),
        _e("pellet_container_content", M, (0, 0, 12011)),
        _e("total_consumption", T, (0, 0, 12016)),
        _e("consumption_since_ash_box_emptied", T, (0, 0, 12013)),
        _e("consumption_since_deashing", T, (0, 0, 12012), enabled=False),
        _e("empty_ash_box_after", N, (0, 0, 12120), enabled=False),
        _e("full_load_hours", T, (0, 0, 12153)),
        _e("full_load_hours_since_service", T, (0, 0, 12404), enabled=False),
        _e("full_load_hours_since_cleaning", T, (0, 0, 15059), enabled=False),
        _e("ignition_count", T, (0, 0, 12018), enabled=False),
        _e("heating_run_count", T, (0, 0, 12017), enabled=False),
        _e("power", W, (0, 0, 12080)),
        _e("fill_pellet_container", W, (0, 0, 12071), enabled=False),
    ),
    ComponentType.PELLET_STORE: (
        _e("state", S, (0, 0, 19417)),
        _e("stock", M, (0, 0, 12015)),
        _e("stock_warning_limit", N, (0, 0, 12042), enabled=False),
        _e("discharge_screw", M, (0, 11029, 0), enabled=False),
    ),
    ComponentType.HEATING_CIRCUIT: (
        _e("state", S, (0, 0, 19404)),
        _e("operating_mode", S, (0, 0, 12092)),
        _e("flow_temperature", M, (0, 11060, 0), (0, 0, 12241)),
        _e("return_temperature", M, (0, 0, 12220)),
        _e("pump", S, (0, 11124, 0), enabled=False),
        _e("curve_offset", N, (0, 0, 12240)),
        _e("flow_at_minus_10", N, (0, 0, 12104), enabled=False),
        _e("flow_at_plus_10", N, (0, 0, 12103), enabled=False),
        _e("setback_reduction", N, (0, 0, 12107), enabled=False),
        _e("heating_limit_day", N, (0, 0, 12096), enabled=False),
        _e("heating_limit_night", N, (0, 0, 12097), enabled=False),
        _e("power", W, (0, 0, 12080)),
        _e("heat_button", W, (0, 0, 12125)),
        _e("auto_button", W, (0, 0, 12126)),
        _e("setback_button", W, (0, 0, 12230)),
        _e("come_button", W, (0, 0, 12218), enabled=False),
        _e("go_button", W, (0, 0, 12231), enabled=False),
    ),
    ComponentType.HOT_WATER: (
        _e("state", S, (0, 0, 19406)),
        _e("temperature", M, (0, 11129, 0), (0, 0, 12271)),
        _e("bottom_temperature", M, (0, 0, 12272), enabled=False),
        _e("target_temperature", N, (0, 0, 12132)),
        _e("charge_now_target_temperature", N, (0, 0, 14257), enabled=False),
        _e("switch_on_difference", N, (0, 0, 12133), enabled=False),
        _e("priority", L, (0, 0, 12770), enabled=False),
        _e("charge_now", W, (0, 0, 12134)),
        _e("power", W, (0, 0, 12080)),
        _e("charging_pump", S, (0, 11131, 0), enabled=False),
    ),
    ComponentType.BUFFER: (_e("top_temperature", M, (0, 0, 12242)),),
    ComponentType.BUFFER_FLEX: (
        _e("state", S, (0, 0, 19403)),
        _e("charge_level", M, (0, 0, 12528)),
        _e("top_temperature", M, (0, 0, 13191), (0, 11327, 0)),
        _e("bottom_temperature", M, (0, 0, 13192)),
        _e("sensor_2_temperature", M, (0, 11328, 0), enabled=False),
        _e("sensor_3_temperature", M, (0, 11329, 0), enabled=False),
        _e("sensor_4_temperature", M, (0, 11330, 0), enabled=False),
        _e("top_target_temperature", M, (0, 0, 13194), enabled=False),
        _e("charge_now", W, (0, 0, 13025)),
        _e("hot_water_charge_now", W, (0, 0, 12134), enabled=False),
        _e("charge_count", T, (0, 0, 15044), enabled=False),
    ),
    ComponentType.SOLAR: (
        _e("state", S, (0, 0, 19408)),
        _e("collector_temperature", M, (0, 11139, 0), (0, 0, 12275)),
        _e("collector_pump", M, (0, 0, 12278), (0, 11142, 0)),
        _e("storage_1_bottom_temperature", M, (0, 0, 12781), enabled=False),
    ),
    ComponentType.SYSTEM: (
        _e("outdoor_temperature", M, (0, 0, 12197), (0, 11127, 0)),
        _e("fault_status", S, (0, 0, 14262), enabled=False),
    ),
}


def get_entry(component: ComponentType, key: str) -> CatalogEntry | None:
    """Look up a catalog entry by component type and key."""
    return next((entry for entry in CATALOG[component] if entry.key == key), None)
