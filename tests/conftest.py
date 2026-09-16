"""Shared fixtures."""

from collections.abc import AsyncIterator

import aiohttp
import pytest

from pyetatouch.client import EtaClient
from tests.fake_heater import FakeHeater, serve


@pytest.fixture
def heater() -> FakeHeater:
    return FakeHeater()


@pytest.fixture
async def client(heater: FakeHeater) -> AsyncIterator[EtaClient]:
    async with serve(heater) as (host, port), aiohttp.ClientSession() as session:
        yield EtaClient(session, host, port, timeout=2)
