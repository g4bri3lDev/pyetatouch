"""Discovery tests: a small handcrafted menu, plus the real menu when available."""

from collections.abc import Callable

from pyetatouch.catalog import ComponentType
from pyetatouch.client import EtaClient
from pyetatouch.discovery import Installation, discover
from pyetatouch.models import VarAddress
from tests.fake_heater import FakeHeater
from tests.helpers import private_fixture, requires_private, varinfo_xml

ON_OFF = {1802: "Aus", 1803: "Ein"}
STATES = {4000: "Ausgeschaltet", 4001: "Bereit", 4002: "Geladen"}

SMALL_VARINFO: dict[tuple[int, int, int], Callable[[str], str]] = {
    (0, 0, 19402): lambda a: varinfo_xml(a, "Kessel", options=STATES),
    (0, 0, 19404): lambda a: varinfo_xml(a, "Heizkreis", options=STATES),
    (0, 0, 19406): lambda a: varinfo_xml(a, "Warmwasserspeicher", options=STATES),
    (0, 0, 12080): lambda a: varinfo_xml(a, "Ein/Aus Taste", writable=True, options=ON_OFF),
    (0, 0, 12240): lambda a: varinfo_xml(
        a, "Schieber Position", writable=True, unit="%", scale=10, limits=(-1000, 0, 1000)
    ),
    (0, 0, 12132): lambda a: varinfo_xml(
        a, "Warmwasserspeicher Soll", writable=True, unit="°C", scale=10, limits=(0, 0, 900)
    ),
}


def small_varinfo(address: str) -> str:
    return SMALL_VARINFO[VarAddress.parse(address).key](address)


def private_varinfo(address: str) -> str:
    # FBH (10102) has the same variables as HK (10101); reuse HK's captures.
    source = address.replace("120/10102/", "120/10101/")
    return private_fixture(f"varinfo/{source.replace('/', '_')}.xml").replace(source, address)


def _small_heater(heater: FakeHeater) -> None:
    heater.varinfo_factory = small_varinfo
    # boiler temperature via its sensor input and the HK status are not readable
    heater.restricted |= {"40/10021/0/11109/0", "120/10101/0/0/12090"}


async def test_components(client: EtaClient, heater: FakeHeater) -> None:
    _small_heater(heater)
    installation = await discover(client)
    assert [(c.name, c.type, c.instance) for c in installation.components] == [
        ("HK", ComponentType.HEATING_CIRCUIT, (120, 10101)),
        ("FBH", ComponentType.HEATING_CIRCUIT, (120, 10102)),
        ("WW", ComponentType.HOT_WATER, (120, 10111)),
        ("Kessel", ComponentType.BOILER, (40, 10021)),
        ("FWM", None, (120, 10999)),
    ]
    assert heater.varsets == {}, "probe variable set must be deleted"


async def test_unknown_component_gets_catalog_variables(
    client: EtaClient, heater: FakeHeater
) -> None:
    _small_heater(heater)
    installation = await discover(client)
    fwm = installation.component_for(VarAddress(120, 10999, 0, 0, 0))
    assert fwm is not None and fwm.type is None
    assert [v.key for v in installation.variables_for(fwm)] == ["outdoor_temperature"]


async def test_restricted_alias_falls_back(client: EtaClient, heater: FakeHeater) -> None:
    _small_heater(heater)
    installation = await discover(client)
    boiler = installation.component_for(VarAddress(40, 10021, 0, 0, 0))
    assert boiler is not None
    by_key = {v.key: v for v in installation.variables_for(boiler)}
    assert by_key["boiler_temperature"].address == VarAddress(40, 10021, 0, 0, 12161)
    assert by_key["flue_gas_temperature"].address == VarAddress(40, 10021, 0, 11110, 0)
    assert set(by_key) == {"boiler_state", "boiler_temperature", "flue_gas_temperature", "power"}


async def test_both_heating_circuits_match(client: EtaClient, heater: FakeHeater) -> None:
    _small_heater(heater)
    installation = await discover(client)
    hk, fbh = (c for c in installation.components if c.type is ComponentType.HEATING_CIRCUIT)
    hk_keys = {v.key for v in installation.variables_for(hk)}
    assert hk_keys == {v.key for v in installation.variables_for(fbh)}
    assert hk_keys == {"heating_circuit_state", "flow_temperature", "curve_offset", "power"}
    assert all(v.address.instance == (120, 10102) for v in installation.variables_for(fbh))


async def test_info_only_for_kinds_that_need_it(client: EtaClient, heater: FakeHeater) -> None:
    _small_heater(heater)
    installation = await discover(client)
    hot_water = next(c for c in installation.components if c.type is ComponentType.HOT_WATER)
    by_key = {v.key: v for v in installation.variables_for(hot_water)}
    assert by_key["hot_water_temperature"].info is None
    target = by_key["hot_water_target_temperature"].info
    assert target is not None and target.writable and target.maximum == 900.0
    power = by_key["power"].info
    assert power is not None and dict(power.options) == ON_OFF
    assert not any(path.endswith("/0/11129/0") for _, path in heater.requests if "varinfo" in path)


async def test_unknown_variables_listed(client: EtaClient, heater: FakeHeater) -> None:
    _small_heater(heater)
    installation = await discover(client)
    unknown = {str(u.address): u.name for u in installation.unknown_variables}
    assert unknown["120/10111/0/0/13987"] == "Ein/Aus Taste anzeigen"
    assert unknown["120/10101/0/0/12090"] == "Status"
    assert unknown["120/10999/0/0/12345"] == "Frischwasser"
    assert "40/10021/0/11109/0" not in unknown


async def test_switch_without_two_options_is_skipped(client: EtaClient, heater: FakeHeater) -> None:
    def varinfo(address: str) -> str:
        if address.endswith("/0/0/12080"):
            return varinfo_xml(address, "Ein/Aus Taste", writable=True, options=STATES)
        return small_varinfo(address)

    heater.varinfo_factory = varinfo
    installation = await discover(client)
    assert all(v.key != "power" for v in installation.variables)


async def test_round_trip(client: EtaClient, heater: FakeHeater) -> None:
    _small_heater(heater)
    installation = await discover(client)
    data = installation.to_dict()
    assert data["version"] == 2
    assert data["components"][-1]["type"] is None
    restored = Installation.from_dict(data)
    assert restored.components == installation.components
    assert restored.variables == installation.variables
    assert restored.unknown_variables == ()


@requires_private
async def test_reference_heater(client: EtaClient, heater: FakeHeater) -> None:
    heater.menu = private_fixture("menu.xml")
    heater.varinfo_factory = private_varinfo
    heater.restricted.add("40/10021/0/11109/0")
    installation = await discover(client)
    assert [c.name for c in installation.components] == [
        "HK",
        "Solar",
        "FBH",
        "Lager",
        "Sys",
        "PufferFlex",
        "WW",
        "Kessel",
    ]
    assert all(c.type is not None for c in installation.components)
    hk, fbh = (c for c in installation.components if c.type is ComponentType.HEATING_CIRCUIT)
    assert {v.key for v in installation.variables_for(hk)} == {
        v.key for v in installation.variables_for(fbh)
    }
