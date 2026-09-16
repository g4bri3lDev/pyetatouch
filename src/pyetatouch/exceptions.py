"""Exceptions raised by pyetatouch."""

from __future__ import annotations


class EtaError(Exception):
    """Base class for all pyetatouch errors."""


class EtaConnectionError(EtaError):
    """The heater could not be reached or the request timed out."""


class EtaWebserviceUnavailableError(EtaConnectionError):
    """The connection was refused; the ETAtouch web service is probably not enabled."""


class EtaNotEtaDeviceError(EtaError):
    """The host answered, but not with an ETAtouch XML document."""


class EtaUnsupportedApiError(EtaError):
    """The heater's API version is older than 1.2."""

    def __init__(self, version: str) -> None:
        super().__init__(f"ETAtouch API version {version!r} is not supported (need >= 1.2)")
        self.version = version


class EtaValidationError(EtaError):
    """A value was rejected client-side before it was sent to the heater."""


class EtaResponseError(EtaError):
    """The heater answered with an <error> document."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.message = message


class EtaPermissionError(EtaResponseError):
    """The variable is not accessible through the web service."""


class EtaNotFoundError(EtaResponseError):
    """The requested resource (e.g. a variable set) does not exist."""


class EtaConflictError(EtaResponseError):
    """The resource already exists or already contains the variable."""


class EtaValueError(EtaResponseError):
    """The heater rejected a written value as out of range."""


class EtaReadOnlyError(EtaResponseError):
    """The heater rejected a write to a read-only variable."""


_MESSAGES: dict[str, type[EtaResponseError]] = {
    "Invalid permission": EtaPermissionError,
    "Variable set not available": EtaNotFoundError,
    "Variable set already exists": EtaConflictError,
    "Can not add the variable to the variable set": EtaConflictError,
    "Value is out of range.": EtaValueError,
    "Read-only parameters must not be written.": EtaReadOnlyError,
}


def error_for(status: int, message: str) -> EtaResponseError:
    """Map an HTTP status and heater error text to the matching exception."""
    message = message.strip()
    cls = _MESSAGES.get(message)
    if cls is None:
        cls = EtaNotFoundError if status == 404 else EtaResponseError
    return cls(status, message)
