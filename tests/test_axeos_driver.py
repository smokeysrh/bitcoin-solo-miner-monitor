import pytest

from bsmm.drivers.axeos import AxeOSDriver
from bsmm.drivers.base import BadResponse, Unreachable
from bsmm.models import Capability
from bsmm.sim.axeos import AxeOSSim

from .conftest import make_client


async def test_probe_recognises_and_names_the_device(client, gamma):
    res = await AxeOSDriver.probe("gamma.test", 80, client=client)
    assert res is not None
    assert res.info.driver == "axeos"
    assert res.info.family == "bitaxe"
    assert res.info.model == "Bitaxe Gamma"
    assert res.info.mac == "AA:BB:CC:00:00:11"
    assert res.info.identity_key == "mac:AA:BB:CC:00:00:11"
    assert res.telemetry is not None and res.telemetry.hashrate_hs and res.telemetry.hashrate_hs > 1e12
    assert res.info.capabilities == [Capability.SCOREBOARD]  # only read-only features are reported


async def test_probe_rejects_things_that_are_not_miners():
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    async def not_a_miner(request):
        return JSONResponse({"hello": "world"})

    import httpx

    app = Starlette(routes=[Route("/api/system/info", not_a_miner)])
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app)) as c:
        assert await AxeOSDriver.probe("x.test", 80, client=c) is None


async def test_probe_unreachable_host_returns_none(client):
    assert await AxeOSDriver.probe("nowhere.test", 80, client=client, timeout=1) is None


async def test_poll_returns_fresh_telemetry_each_time(client, gamma):
    d = AxeOSDriver("gamma.test", 80, client=client)
    t1 = await d.poll()
    t2 = await d.poll()
    assert t1.pools and t1.pools[0].active
    assert t2.uptime_s is not None and t1.uptime_s is not None and t2.uptime_s >= t1.uptime_s
    assert d.last_raw is not None and d.last_raw["ASICModel"] == "BM1370"


async def test_poll_raises_unreachable_then_recovers(gamma):
    c = make_client({"gamma.test": gamma})
    d = AxeOSDriver("gone.test", 80, client=c)
    with pytest.raises(Unreachable):
        await d.poll()
    d2 = AxeOSDriver("gamma.test", 80, client=c)
    gamma.fail_next = 5
    with pytest.raises(BadResponse):
        await d2.poll()
    gamma.fail_next = 0
    assert (await d2.poll()).online
    await c.aclose()


async def test_a_paused_miner_reads_as_paused_with_no_hashrate(client, gamma):
    d = AxeOSDriver("gamma.test", 80, client=client)
    t = await d.poll()
    assert t.mining_paused is False and t.hashrate_hs and t.hashrate_hs > 0
    gamma.paused = True  # the miner was paused at the device, not through this app
    t = await d.poll()
    assert t.mining_paused is True and (t.hashrate_hs or 0) == 0


async def test_nerdqaxe_profile_is_named_from_device_model():
    sim = AxeOSSim("nerdqaxe", seed=3)
    async with make_client({"n.test": sim}) as c:
        res = await AxeOSDriver.probe("n.test", 80, client=c)
    assert res is not None
    assert res.info.family == "nerdqaxe" and res.info.model == "NerdQAxe++"
    assert res.info.asic_count == 4
