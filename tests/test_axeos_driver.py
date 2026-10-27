import pytest

from bsmm.drivers.axeos import AxeOSDriver
from bsmm.drivers.base import ActionFailed, BadResponse, Unreachable, Unsupported
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
    assert Capability.RESTART in res.info.capabilities and Capability.PAUSE in res.info.capabilities


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


async def test_restart_and_identify(client, gamma):
    d = AxeOSDriver("gamma.test", 80, client=client)
    assert (await d.restart()).ok
    assert (await d.identify()).ok
    assert gamma.restarts == 1 and gamma.identified == 1
    assert ("POST", "/api/system/restart", None) in gamma.calls


async def test_pause_resume(client, gamma):
    d = AxeOSDriver("gamma.test", 80, client=client)
    await d.pause()
    t = await d.poll()
    assert t.mining_paused is True and (t.hashrate_hs or 0) == 0
    await d.resume()
    t = await d.poll()
    assert t.mining_paused is False and t.hashrate_hs and t.hashrate_hs > 0


async def test_set_pool_primary_and_fallback(client, gamma):
    d = AxeOSDriver("gamma.test", 80, client=client)
    await d.set_pool(url="stratum+tcp://10.0.0.5", port=3333, user="bc1qexample.rig1", password="secret")
    sent = [c for c in gamma.calls if c[0] == "PATCH"][-1][2]
    assert sent == {
        "stratumURL": "10.0.0.5",
        "stratumPort": 3333,
        "stratumUser": "bc1qexample.rig1",
        "stratumPassword": "secret",
    }
    await d.set_pool(url="solo.ckpool.org", port=3333, user="bc1qexample.rig1", role="fallback", tls=False)
    sent = [c for c in gamma.calls if c[0] == "PATCH"][-1][2]
    assert sent["fallbackStratumURL"] == "solo.ckpool.org" and sent["fallbackStratumTLS"] == 0
    t = await d.poll()
    assert t.pools[0].url == "10.0.0.5" and t.pools[0].port == 3333


async def test_set_pool_validates_input(client):
    d = AxeOSDriver("gamma.test", 80, client=client)
    with pytest.raises(ActionFailed):
        await d.set_pool(url="", port=3333, user="x")
    with pytest.raises(ActionFailed):
        await d.set_pool(url="h", port=70000, user="x")


async def test_set_fan_validation(client, gamma):
    d = AxeOSDriver("gamma.test", 80, client=client)
    await d.set_fan(auto=False, speed_pct=70)
    assert gamma.settings["autofanspeed"] == 0 and gamma.settings["manualFanSpeed"] == 70
    await d.set_fan(auto=True, temp_target_c=58)
    assert gamma.settings["temptarget"] == 58
    with pytest.raises(ActionFailed):
        await d.set_fan(speed_pct=101)
    with pytest.raises(ActionFailed):
        await d.set_fan(temp_target_c=95)
    with pytest.raises(ActionFailed):
        await d.set_fan()  # nothing to change


async def test_tuning_only_allows_values_the_device_lists(client, gamma):
    d = AxeOSDriver("gamma.test", 80, client=client)
    opts = await d.tuning_options()
    assert opts is not None and 525 in opts.frequency_mhz and 1150 in opts.core_voltage_mv
    await d.set_tuning(frequency_mhz=550, core_voltage_mv=1200)
    assert gamma.settings["frequency"] == 550 and gamma.settings["coreVoltage"] == 1200
    with pytest.raises(ActionFailed):
        await d.set_tuning(frequency_mhz=999)
    with pytest.raises(ActionFailed):
        await d.set_tuning(core_voltage_mv=1500)
    assert gamma.settings["frequency"] == 550  # untouched by the rejected calls


async def test_tuning_refused_when_firmware_does_not_publish_ranges(gamma):
    # Remove /api/system/asic by pointing at an app that lacks it.
    import httpx
    from starlette.applications import Starlette
    from starlette.routing import Route

    base = gamma.app()
    routes = [r for r in base.routes if getattr(r, "path", "") != "/api/system/asic"]
    app = Starlette(routes=[Route(r.path, r.endpoint, methods=list(r.methods or [])) for r in routes])  # type: ignore[attr-defined]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app)) as c:
        d = AxeOSDriver("gamma.test", 80, client=c)
        with pytest.raises(Unsupported):
            await d.set_tuning(frequency_mhz=525)


async def test_unsupported_action_is_remembered(gamma):
    import httpx
    from starlette.applications import Starlette
    from starlette.routing import Route

    app = Starlette(routes=[Route("/api/system/info", lambda r: None)])
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app)) as c:
        d = AxeOSDriver("x.test", 80, client=c)
        with pytest.raises(Unsupported):
            await d.identify()
        assert "identify" in d._unsupported


async def test_nerdqaxe_profile_is_named_from_device_model():
    sim = AxeOSSim("nerdqaxe", seed=3)
    async with make_client({"n.test": sim}) as c:
        res = await AxeOSDriver.probe("n.test", 80, client=c)
    assert res is not None
    assert res.info.family == "nerdqaxe" and res.info.model == "NerdQAxe++"
    assert res.info.asic_count == 4
