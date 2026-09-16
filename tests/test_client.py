"""Tests for EtaClient against the fake heater."""

import aiohttp
import pytest

from pyetatouch.client import EtaClient
from pyetatouch.exceptions import (
    EtaConflictError,
    EtaConnectionError,
    EtaNotEtaDeviceError,
    EtaNotFoundError,
    EtaPermissionError,
    EtaUnsupportedApiError,
    EtaValidationError,
    EtaValueError,
    EtaWebserviceUnavailableError,
)
from pyetatouch.models import VarAddress
from tests.fake_heater import FakeHeater, Value, serve
from tests.helpers import load_fixture

HYSTERESIS = VarAddress.parse("120/10111/0/0/12133")
WW_ON_OFF = VarAddress.parse("120/10111/0/0/12080")
BOILER_TEMP = VarAddress.parse("40/10021/0/11109/0")


async def test_api_version(client: EtaClient) -> None:
    assert await client.check_api() == "1.2"


async def test_old_api_rejected(client: EtaClient, heater: FakeHeater) -> None:
    heater.api = load_fixture("api_1_1.xml")
    with pytest.raises(EtaUnsupportedApiError):
        await client.check_api()


@pytest.mark.parametrize(("status", "body"), [(200, load_fixture("not_eta.html")), (404, "")])
async def test_not_an_eta_device(
    client: EtaClient, heater: FakeHeater, status: int, body: str
) -> None:
    heater.responses[("GET", "/user/api")] = (status, body)
    with pytest.raises(EtaNotEtaDeviceError):
        await client.api_version()


async def test_timeout(heater: FakeHeater) -> None:
    heater.delays["/user/api"] = 1.0
    async with serve(heater) as (host, port), aiohttp.ClientSession() as session:
        client = EtaClient(session, host, port, timeout=0.1)
        with pytest.raises(EtaConnectionError) as info:
            await client.api_version()
    assert not isinstance(info.value, EtaWebserviceUnavailableError)


async def test_connection_refused_means_webservice_unavailable(unused_tcp_port: int) -> None:
    async with aiohttp.ClientSession() as session:
        client = EtaClient(session, "127.0.0.1", unused_tcp_port, timeout=2)
        with pytest.raises(EtaWebserviceUnavailableError):
            await client.api_version()


async def test_menu(client: EtaClient) -> None:
    assert len(await client.menu()) == 5


async def test_read(client: EtaClient, heater: FakeHeater) -> None:
    heater.values[str(BOILER_TEMP)] = Value("600", "60", "°C", 10)
    value = await client.read(BOILER_TEMP)
    assert value.address == BOILER_TEMP
    assert value.raw == 600.0


async def test_read_permission_error(client: EtaClient, heater: FakeHeater) -> None:
    heater.restricted.add("120/10101/0/0/12090")
    with pytest.raises(EtaPermissionError):
        await client.read(VarAddress.parse("120/10101/0/0/12090"))


async def test_var_info_is_cached(client: EtaClient, heater: FakeHeater) -> None:
    heater.varinfo[str(HYSTERESIS)] = load_fixture("varinfo_hysteresis.xml")
    first = await client.var_info(HYSTERESIS)
    assert await client.var_info(HYSTERESIS) is first
    assert heater.requests.count(("GET", f"/user/varinfo/{HYSTERESIS}")) == 1


async def test_var_info_refresh(client: EtaClient, heater: FakeHeater) -> None:
    heater.varinfo[str(HYSTERESIS)] = load_fixture("varinfo_hysteresis.xml")
    first = await client.var_info(HYSTERESIS)
    assert await client.var_info(HYSTERESIS, refresh=True) is not first


async def test_write_scaled_number(client: EtaClient, heater: FakeHeater) -> None:
    heater.varinfo[str(HYSTERESIS)] = load_fixture("varinfo_hysteresis.xml")
    await client.write(HYSTERESIS, 8)
    assert heater.writes == [(str(HYSTERESIS), "80")]


async def test_write_option_label(client: EtaClient, heater: FakeHeater) -> None:
    heater.varinfo[str(WW_ON_OFF)] = load_fixture("varinfo_ww_on_off.xml")
    await client.write(WW_ON_OFF, "Ein")
    assert heater.writes == [(str(WW_ON_OFF), "1803")]


async def test_write_read_only_is_not_sent(client: EtaClient, heater: FakeHeater) -> None:
    heater.varinfo[str(BOILER_TEMP)] = load_fixture("varinfo_boiler_temperature.xml")
    with pytest.raises(EtaValidationError):
        await client.write(BOILER_TEMP, 50)
    assert heater.writes == []


async def test_write_rejected_by_heater(client: EtaClient, heater: FakeHeater) -> None:
    heater.write_errors[str(HYSTERESIS)] = (400, "Value is out of range.")
    with pytest.raises(EtaValueError):
        await client.write_raw(HYSTERESIS, 950)


async def test_errors(client: EtaClient, heater: FakeHeater) -> None:
    heater.errors = load_fixture("errors_active.xml")
    (fault,) = await client.errors()
    assert fault.fub_name == "Kessel"


async def test_varset_endpoints(client: EtaClient, heater: FakeHeater) -> None:
    heater.values[str(BOILER_TEMP)] = Value("600", "60", "°C", 10)
    await client.create_varset("test")
    await client.add_to_varset("test", BOILER_TEMP)
    values = await client.read_varset("test")
    assert values[BOILER_TEMP].raw == 600.0
    await client.delete_varset("test")
    assert heater.varsets == {}


async def test_varset_errors(client: EtaClient) -> None:
    await client.create_varset("test")
    with pytest.raises(EtaConflictError):
        await client.create_varset("test")
    await client.add_to_varset("test", BOILER_TEMP)
    with pytest.raises(EtaConflictError):
        await client.add_to_varset("test", BOILER_TEMP)
    with pytest.raises(EtaNotFoundError):
        await client.read_varset("missing")
    with pytest.raises(EtaNotFoundError):
        await client.delete_varset("missing")


async def test_client_builds_varset(client: EtaClient) -> None:
    varset = client.varset("ha1", [BOILER_TEMP])
    assert varset.name == "ha1"
