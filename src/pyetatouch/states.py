"""Stable, language-independent keys for ETAtouch option codes.

The heater labels option codes in the panel language; the codes themselves are the
same on every heater. Consumers use these keys (e.g. as translation keys) instead of
the labels. Unknown codes map to ``code_<code>``.
"""

from __future__ import annotations

from collections.abc import Mapping

from .exceptions import EtaValidationError
from .models import VarInfo

STATE_KEYS: Mapping[int, str] = {
    # component state (boiler, heating circuit, hot water, buffer, solar, discharge)
    4000: "off",
    4001: "ready",
    4002: "charged",
    4003: "full",
    4004: "deashing",
    4005: "changing_position",
    4006: "flushing",
    4007: "starting",
    4008: "on",
    4009: "running",
    4010: "conveying",
    4011: "heating",
    4012: "setback",
    4013: "charging",
    4014: "shutting_down",
    4015: "ember_burnout",
    4016: "fault",
    4017: "locked",
    4018: "ember_burnout_locked",
    4019: "pellet_mode",
    4021: "switching_to_log_wood",
    # outputs (pumps, ignition, suction turbine)
    1040: "off",
    1041: "on",
    1042: "locked",
    1043: "fuse_defective",
    1044: "no_terminal",
    1045: "terminal_unavailable",
    # inputs (ash box)
    1070: "no",
    1071: "yes",
    1072: "locked",
    1073: "fuse_defective",
    1074: "no_terminal",
    1075: "terminal_unavailable",
    # pellet container
    3640: "not_full",
    3641: "demand",
    3642: "suction",
    3643: "discharge_overrun",
    3644: "turbine_overrun",
    3645: "full",
    3646: "overrun_standby",
    3647: "standby_boiler",
    3648: "standby_discharge",
    3649: "discharge_error",
    3650: "suction_time_exceeded",
    # heating circuit operating mode
    2301: "heating",
    2302: "setback",
    2303: "heating",
    2304: "setback",
    2305: "off",
    2306: "vacation",
    2307: "screed_drying",
    # fault status
    1050: "error",
    1051: "ok",
    # priority
    1971: "low",
    1972: "medium",
    1973: "high",
}


def state_key(code: int) -> str:
    """Return the stable key of an option code."""
    return STATE_KEYS.get(code, f"code_{code}")


def state_keys(info: VarInfo) -> list[str]:
    """Return the distinct keys of a variable's options, in option order."""
    return list(dict.fromkeys(state_key(code) for code in info.options))


def code_for_state(info: VarInfo, key: str) -> int:
    """Return the first option code of a variable that has the given key."""
    for code in info.options:
        if state_key(code) == key:
            return code
    raise EtaValidationError(f"{key!r} is not an option of {info.name}")
