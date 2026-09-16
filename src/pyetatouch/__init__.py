"""Async client for the ETAtouch REST web service."""

from .catalog import CATALOG, CatalogEntry, ComponentType, Kind, component_type, get_entry
from .client import EtaClient
from .discovery import (
    Component,
    Installation,
    MatchedVariable,
    UnknownComponent,
    UnknownVariable,
    discover,
)
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
from .transport import Transport
from .varset import VarSet

__version__ = "0.0.0"

__all__ = [
    "CATALOG",
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
    "UnknownComponent",
    "UnknownVariable",
    "VarAddress",
    "VarInfo",
    "VarSet",
    "VarValue",
    "component_type",
    "decode_value",
    "discover",
    "encode_value",
    "get_entry",
    "switch_codes",
]
