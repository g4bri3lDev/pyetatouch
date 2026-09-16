"""Tests for the command-line interface."""

import pytest

from pyetatouch.__main__ import async_main
from tests.fake_heater import FakeHeater, Value, serve
from tests.helpers import load_fixture

HYSTERESIS = "120/10111/0/0/12133"
PRIORITY = "120/10111/0/0/12770"


def _prepare(heater: FakeHeater) -> None:
    heater.values[HYSTERESIS] = Value("70", "7", "°C", 10)
    heater.varinfo[HYSTERESIS] = load_fixture("varinfo_hysteresis.xml")
    heater.values[PRIORITY] = Value("1973", "xxx", offset=1971)
    heater.varinfo[PRIORITY] = load_fixture("varinfo_ww_priority.xml")


async def test_read(heater: FakeHeater, capsys: pytest.CaptureFixture[str]) -> None:
    _prepare(heater)
    async with serve(heater) as (host, port):
        assert await async_main(["--port", str(port), "read", host, HYSTERESIS]) == 0
        assert await async_main(["--port", str(port), "read", host, PRIORITY]) == 0
    out = capsys.readouterr().out
    assert "Einschaltdifferenz: 7.0 °C" in out
    assert "Priorität: Hoch" in out


async def test_write_requires_yes(heater: FakeHeater, capsys: pytest.CaptureFixture[str]) -> None:
    _prepare(heater)
    async with serve(heater) as (host, port):
        assert await async_main(["--port", str(port), "write", host, HYSTERESIS, "8"]) == 2
    assert "--yes" in capsys.readouterr().out
    assert heater.writes == []


async def test_write_with_yes(heater: FakeHeater, capsys: pytest.CaptureFixture[str]) -> None:
    _prepare(heater)
    async with serve(heater) as (host, port):
        args = ["--port", str(port), "write", host, PRIORITY, "Mittel", "--yes"]
        assert await async_main(args) == 0
    assert heater.writes == [(PRIORITY, "1972")]


async def test_discover(heater: FakeHeater, capsys: pytest.CaptureFixture[str]) -> None:
    heater.varinfo_factory = lambda address: load_fixture("varinfo_ww_on_off.xml").replace(
        "120/10111/0/0/12080", address
    )
    async with serve(heater) as (host, port):
        assert await async_main(["--port", str(port), "discover", host]) == 0
    out = capsys.readouterr().out
    assert "FBH [heating_circuit] 120/10102" in out
    assert "unknown components: 1" in out


async def test_error_exit_code(unused_tcp_port: int, capsys: pytest.CaptureFixture[str]) -> None:
    assert await async_main(["--port", str(unused_tcp_port), "discover", "127.0.0.1"]) == 1
    assert "error:" in capsys.readouterr().err
