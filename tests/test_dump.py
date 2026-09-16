"""Tests for the structure dump."""

import json

from pyetatouch.client import EtaClient
from pyetatouch.dump import describe
from tests.fake_heater import FakeHeater, Value
from tests.helpers import varinfo_xml


def _heater(heater: FakeHeater) -> None:
    heater.varinfo_factory = lambda address: varinfo_xml(
        address, "X", writable=True, options={1802: "Aus", 1803: "Ein"}
    )
    heater.restricted.add("120/10101/0/0/12090")
    heater.values["40/10021/0/11109/0"] = Value("600", "60", "°C", 10)


async def test_describe_anonymised(client: EtaClient, heater: FakeHeater) -> None:
    _heater(heater)
    calls: list[tuple[int, int]] = []
    report = await describe(client, progress=lambda done, total: calls.append((done, total)))
    assert report["api"] == "1.2"
    assert [c["name"] for c in report["components"]] == [
        "heating_circuit 1",
        "heating_circuit 2",
        "hot_water 1",
        "boiler 1",
        "component 1",
    ]
    hk = report["components"][0]
    assert hk["fub"] == 10101 and hk["type"] == "heating_circuit"
    by_id = {v["id"]: v for v in hk["variables"]}
    assert by_id["0/0/12080"]["catalog"] == "power"
    assert by_id["0/0/12080"]["options"] == {"1802": "Aus", "1803": "Ein"}
    assert by_id["0/0/12090"] == {
        "id": "0/0/12090",
        "name": "Status",
        "catalog": None,
        "error": "Invalid permission",
    }
    text = json.dumps(report)
    assert "600" not in text and '"node"' not in text and "HK" not in text
    assert calls[-1][0] == calls[-1][1] == sum(len(c["variables"]) for c in report["components"])


async def test_describe_without_info_keeps_names(client: EtaClient, heater: FakeHeater) -> None:
    _heater(heater)
    report = await describe(client, with_info=False, keep_names=True)
    assert report["components"][0]["name"] == "HK"
    assert set(report["components"][0]["variables"][0]) == {"id", "name", "catalog"}
    assert not any("varinfo" in path for _, path in heater.requests)
