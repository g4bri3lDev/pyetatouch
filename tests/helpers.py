"""Helpers for loading XML fixtures."""

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
PRIVATE = FIXTURES / "private"
NS_URI = "http://www.eta.co.at/rest/v1"

requires_private = pytest.mark.skipif(
    not (PRIVATE / "menu.xml").exists(),
    reason="private captures of the reference heater are not available",
)


def load_fixture(name: str) -> str:
    """Return the text of a committed fixture file relative to tests/fixtures."""
    return (FIXTURES / name).read_text(encoding="utf-8")


def private_fixture(name: str) -> str:
    """Return the text of a local-only capture relative to tests/fixtures/private."""
    return (PRIVATE / name).read_text(encoding="utf-8")


def varinfo_xml(
    address: str,
    name: str,
    *,
    writable: bool = False,
    unit: str = "",
    scale: int = 1,
    limits: tuple[int, int, int] | None = None,
    options: dict[int, str] | None = None,
) -> str:
    """Build a /user/varinfo document in the heater's format."""
    valid = ""
    if options:
        valid = "".join(
            f'<value strValue="{label}">{code}</value>' for code, label in options.items()
        )
    elif limits:
        low, default, high = limits
        valid = f"<min>{low}</min><def>{default}</def><max>{high}</max>"
    valid_block = f"<validValues>{valid}</validValues>" if valid else ""
    kind = "TEXT" if options else "DEFAULT"
    offset = min(options) if options else 0
    return (
        f'<?xml version="1.0" encoding="utf-8"?><eta version="1.0" xmlns="{NS_URI}">'
        f'<varInfo uri="/user/varinfo/{address}"><variable advTextOffset="{offset}" unit="{unit}" '
        f'uri="{address}" isWritable="{int(writable)}" scaleFactor="{scale}" name="{name}" '
        f'fullName="Test > {name}" decPlaces="0"><type>{kind}</type>{valid_block}'
        f"</variable></varInfo></eta>"
    )
