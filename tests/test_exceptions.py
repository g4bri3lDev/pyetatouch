"""Tests for the exception mapping."""

import pytest

from pyetatouch.exceptions import (
    EtaConflictError,
    EtaConnectionError,
    EtaError,
    EtaNotFoundError,
    EtaPermissionError,
    EtaReadOnlyError,
    EtaResponseError,
    EtaUnsupportedApiError,
    EtaValueError,
    EtaWebserviceUnavailableError,
    error_for,
)


@pytest.mark.parametrize(
    ("status", "message", "expected"),
    [
        (400, "Invalid permission", EtaPermissionError),
        (404, "Variable set not available", EtaNotFoundError),
        (400, "Variable set already exists", EtaConflictError),
        (400, "Can not add the variable to the variable set", EtaConflictError),
        (400, "Value is out of range.", EtaValueError),
        (400, "Read-only parameters must not be written.", EtaReadOnlyError),
        (404, "Something new", EtaNotFoundError),
        (400, "Something new", EtaResponseError),
    ],
)
def test_error_for_maps_heater_messages(
    status: int, message: str, expected: type[EtaResponseError]
) -> None:
    error = error_for(status, message)
    assert type(error) is expected
    assert error.status == status
    assert error.message == message


def test_error_for_strips_whitespace() -> None:
    assert type(error_for(400, "  Invalid permission\n")) is EtaPermissionError


def test_hierarchy() -> None:
    assert issubclass(EtaWebserviceUnavailableError, EtaConnectionError)
    assert issubclass(EtaResponseError, EtaError)
    error = EtaUnsupportedApiError("1.1")
    assert error.version == "1.1"
    assert "1.1" in str(error)
