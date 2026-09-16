"""Async client for the ETAtouch REST web service."""

from .catalog import (
    CATALOG,
    CatalogEntry,
    ComponentType,
    Kind,
    component_type,
    enabled_by_default,
    entry_for_alias,
    get_entry,
)
from .client import EtaClient
from .discovery import (
    Component,
    Installation,
    MatchedVariable,
    UnknownVariable,
    discover,
)
from .dump import describe
from .exceptions import (
    EtaConflictError,
    EtaConnectionError,
    EtaError,
    EtaNotEtaDeviceError,
    EtaNotFoundError,
    EtaPermissionError,
    EtaReadOnlyError,
    EtaResponseError,
    EtaUnsupportedApiError,
    EtaValidationError,
    EtaValueError,
    EtaWebserviceUnavailableError,
)
from .models import (
    EtaFault,
    MenuFub,
    VarAddress,
    VarInfo,
    VarValue,
    decode_value,
    encode_value,
    switch_codes,
)
from .states import STATE_KEYS, code_for_state, state_key, state_keys
from .transport import Transport
from .varset import VarSet

__version__ = "0.0.0"

__all__ = [
    "CATALOG",
    "STATE_KEYS",
    "CatalogEntry",
    "Component",
    "ComponentType",
    "EtaClient",
    "EtaConflictError",
    "EtaConnectionError",
    "EtaError",
    "EtaFault",
    "EtaNotEtaDeviceError",
    "EtaNotFoundError",
    "EtaPermissionError",
    "EtaReadOnlyError",
    "EtaResponseError",
    "EtaUnsupportedApiError",
    "EtaValidationError",
    "EtaValueError",
    "EtaWebserviceUnavailableError",
    "Installation",
    "Kind",
    "MatchedVariable",
    "MenuFub",
    "Transport",
    "UnknownVariable",
    "VarAddress",
    "VarInfo",
    "VarSet",
    "VarValue",
    "code_for_state",
    "component_type",
    "decode_value",
    "describe",
    "discover",
    "enabled_by_default",
    "encode_value",
    "entry_for_alias",
    "get_entry",
    "state_key",
    "state_keys",
    "switch_codes",
]
