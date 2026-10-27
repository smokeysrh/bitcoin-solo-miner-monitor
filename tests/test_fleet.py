import time

import pytest

from bsmm.drivers.base import Unsupported
from bsmm.engine.fleet import build_summary, derive_status
from bsmm.models import Capability, DeviceStatus, Severity, Telemetry
from bsmm.settings import Settings
from bsmm.sim.axeos import AxeOSSim


async def add(ctx, hosts, host, sim, **kw):
    hosts[host] = sim.app()
    # only the AxeOS driver: the cgminer driver would open real sockets to the fake host names
    res = await ctx.fleet.add_by_host(host, drivers=["axeos"], **kw)
    return res


async def poll(ctx, device_id):
    rt = ctx.fleet.runtimes[device_id]
    await ctx.fleet._poll_once(rt)
    return rt


async def events(ctx, **kw):
    return [e.type for e in await ctx.store.list_events(limit=200, **kw)]


async def test_add_poll_and_view(lan):
    ctx, hosts = lan
    res = await add(ctx, hosts, "gamma.test", AxeOSSim("gamma", seed=1, mac="AA:BB:CC:00:00:11"), name="Garage")
    assert res.created and res.device.name == "Garage" and res.device.family == "bitaxe"
    rt = await poll(ctx, res.device.id)
    view = ctx.fleet.view(res.device.id)
    assert view and view.status == DeviceStatus.ONLINE
    assert view.telemetry and view.telemetry.hashrate_hs and view.hashrate_smooth_hs
    assert view.web_url == "http://gamma.test"
    assert rt.failures == 0
    assert "device_added" in await events(ctx)


async def test_same_miner_on_two_ips_is_not_added_twice(lan):
    ctx, hosts = lan
    sim = AxeOSSim("gamma", seed=1, mac="AA:BB:CC:2B:42:E4")
    first = await add(ctx, hosts, "10.0.0.88", sim)
    hosts["10.0.0.252"] = sim.app()  # same box, second address (the real Magic Miner does this)
    second = await ctx.fleet.add_by_host("10.0.0.252", drivers=["axeos"])
    assert first.created and not second.created and second.merged
    assert second.device.id == first.device.id
    assert "10.0.0.252" in second.device.alt_hosts
    assert len(ctx.fleet.views()) == 1
    assert "also answers on 10.0.0.252" in (second.note or "")


async def test_unknown_host_gives_a_helpful_error(lan):
    ctx, _ = lan
    with pytest.raises(LookupError, match="looks like a supported miner"):
        await ctx.fleet.add_by_host("10.9.9.9", drivers=["axeos"])


async def test_offline_after_n_failures_then_recovery(lan):
    ctx, hosts = lan
    sim = AxeOSSim("gamma", seed=2, mac="AA:BB:CC:00:00:22")
    res = await add(ctx, hosts, "g.test", sim, name="G")
    rt = await poll(ctx, res.device.id)
    assert rt.status == DeviceStatus.ONLINE
    del hosts["g.test"]  # unplugged
    await poll(ctx, res.device.id)
    await poll(ctx, res.device.id)
    assert rt.status == DeviceStatus.ONLINE  # two failures are tolerated (default is 3)
    await poll(ctx, res.device.id)
    assert rt.status == DeviceStatus.OFFLINE and rt.last_error
    assert "device_offline" in await events(ctx)
    hosts["g.test"] = sim.app()  # plugged back in
    await poll(ctx, res.device.id)
    assert rt.status == DeviceStatus.ONLINE and rt.failures == 0
    kinds = await events(ctx)
    assert "device_online" in kinds
    ev = (await ctx.store.list_events(types=["device_offline"]))[0]
    assert ev.severity == Severity.CRITICAL and "G is offline" in ev.title


async def test_restart_grace_suppresses_offline_alarm(lan):
    ctx, hosts = lan
    sim = AxeOSSim("gamma", seed=3, mac="AA:BB:CC:00:00:33")
    res = await add(ctx, hosts, "g.test", sim)
    rt = await poll(ctx, res.device.id)
    ctx.settings.current.safety.allow_control = True
    out = await ctx.fleet.run_action(res.device.id, "restart", actor="test")
    assert out["ok"] and sim.restarts == 1
    del hosts["g.test"]
    for _ in range(4):
        await poll(ctx, res.device.id)
    assert rt.status == DeviceStatus.DEGRADED and rt.status_reason == "Restarting"
    assert "device_offline" not in await events(ctx)
    hosts["g.test"] = sim.app()
    await poll(ctx, res.device.id)
    assert rt.status == DeviceStatus.ONLINE


async def test_event_detection_restart_fallback_best_share(lan):
    ctx, hosts = lan
    sim = AxeOSSim("gamma", seed=4, mac="AA:BB:CC:00:00:44")
    res = await add(ctx, hosts, "g.test", sim)
    await poll(ctx, res.device.id)
    # restart
    sim.started = time.time()
    sim.settings["_x"] = 1
    await poll(ctx, res.device.id)
    # the sim reports uptime from `started`; push it back so the next reading looks like a reboot
    sim.started = time.time() - 3600
    await poll(ctx, res.device.id)
    sim.started = time.time()
    await poll(ctx, res.device.id)
    # fallback pool
    orig = sim.info

    def info_fallback():
        d = orig()
        d["isUsingFallbackStratum"] = 1
        return d

    sim.info = info_fallback  # type: ignore[method-assign]
    await poll(ctx, res.device.id)
    # new best share
    sim.best_diff *= 5
    await poll(ctx, res.device.id)
    kinds = await events(ctx)
    assert "device_restarted" in kinds
    assert "pool_failover" in kinds
    assert "new_best_share" in kinds
    best = (await ctx.store.list_events(types=["new_best_share"]))[0]
    assert best.severity == Severity.SUCCESS and best.data["difficulty"] > best.data["previous"]


async def test_device_reported_block_counter_raises_block_found(lan):
    ctx, hosts = lan
    sim = AxeOSSim("gamma", seed=5, mac="AA:BB:CC:00:00:55")
    res = await add(ctx, hosts, "g.test", sim)
    await poll(ctx, res.device.id)
    sim.blocks_found = 1
    sub = ctx.bus.subscribe({"block_found"})
    await poll(ctx, res.device.id)
    assert "block_found" in await events(ctx)
    msg = await sub.get(timeout=1)
    assert msg and msg.data["device_id"] == res.device.id


async def test_summary_totals_and_efficiency(lan):
    ctx, hosts = lan
    a = await add(ctx, hosts, "a.test", AxeOSSim("gamma", seed=6, mac="AA:BB:CC:00:00:66"))
    b = await add(ctx, hosts, "b.test", AxeOSSim("nerdqaxe", seed=7, mac="AA:BB:CC:00:00:77"))
    await poll(ctx, a.device.id)
    await poll(ctx, b.device.id)
    s = ctx.fleet.summary(fresh=True)
    assert s.devices_total == 2 and s.devices_online == 2
    assert s.hashrate_hs == pytest.approx(5.95e12, rel=0.1)
    assert s.power_w and 100 < s.power_w < 130
    assert s.efficiency_j_th == pytest.approx(s.power_w / (s.hashrate_hs / 1e12), rel=0.02)
    assert s.best_diff and s.best_diff_device_id in {a.device.id, b.device.id}
    assert s.pools and s.pools[0].devices == 2 and not s.pools[0].is_fallback
    assert s.addresses == ["bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"]
    assert ctx.fleet.all_addresses() == s.addresses


async def test_samples_are_written_and_queryable(lan):
    ctx, hosts = lan
    a = await add(ctx, hosts, "a.test", AxeOSSim("gamma", seed=8, mac="AA:BB:CC:00:00:88"))
    for _ in range(3):
        await poll(ctx, a.device.id)
    await ctx.fleet._flush_samples()
    h = await ctx.store.samples.history(metrics=["hashrate_hs", "power_w"], start=time.time() - 600, end=time.time() + 5, step=10)
    assert any(v for v in h.series["hashrate_hs"])


async def test_control_guard_rails(lan):
    ctx, hosts = lan
    sim = AxeOSSim("gamma", seed=9, mac="AA:BB:CC:00:00:99")
    res = await add(ctx, hosts, "g.test", sim)
    await poll(ctx, res.device.id)
    dev_id = res.device.id
    # tuning is off by default
    with pytest.raises(PermissionError, match="Frequency/voltage"):
        await ctx.fleet.run_action(dev_id, "set_tuning", {"frequency_mhz": 550})
    await ctx.settings.update({"safety": {"allow_tuning": True}})
    out = await ctx.fleet.run_action(dev_id, "set_tuning", {"frequency_mhz": 550, "core_voltage_mv": 1200})
    assert out["ok"] and sim.settings["frequency"] == 550
    # a global kill switch
    await ctx.settings.update({"safety": {"allow_control": False}})
    with pytest.raises(PermissionError, match="switched off in Settings"):
        await ctx.fleet.run_action(dev_id, "restart")
    await ctx.settings.update({"safety": {"allow_control": True}})
    # per-device kill switch
    await ctx.fleet.update(dev_id, {"allow_control": False})
    with pytest.raises(PermissionError, match="switched off for"):
        await ctx.fleet.run_action(dev_id, "restart")
    await ctx.fleet.update(dev_id, {"allow_control": True})
    # unknown / unsupported
    with pytest.raises(ValueError, match="unknown action"):
        await ctx.fleet.run_action(dev_id, "format_disk")
    ctx.fleet.runtimes[dev_id].device.capabilities.remove(Capability.RESTART)
    with pytest.raises(Unsupported):
        await ctx.fleet.run_action(dev_id, "restart")
    # dry run touches nothing
    calls = len(sim.calls)
    ctx.fleet.runtimes[dev_id].device.capabilities.append(Capability.SET_POOL)
    dry = await ctx.fleet.run_action(dev_id, "set_pool", {"url": "x", "port": 1, "user": "u", "password": "secret"}, dry_run=True)
    assert dry["dry_run"] and dry["params"]["password"] == "***" and len(sim.calls) == calls
    # everything above was audited (secrets redacted)
    audit = await ctx.store.list_audit()
    assert any(a["action"] == "set_tuning" and a["result"]["ok"] for a in audit)


async def test_tuning_blocked_when_device_is_hot(lan):
    ctx, hosts = lan
    sim = AxeOSSim("gamma", seed=10, mac="AA:BB:CC:00:00:AA")
    res = await add(ctx, hosts, "g.test", sim)
    rt = await poll(ctx, res.device.id)
    await ctx.settings.update({"safety": {"allow_tuning": True, "max_temp_c": 60}})
    rt.telemetry.temp_asic_c = 72.0  # type: ignore[union-attr]
    from bsmm.drivers.base import ActionFailed

    with pytest.raises(ActionFailed, match="cool it down"):
        await ctx.fleet.run_action(res.device.id, "set_tuning", {"frequency_mhz": 550})


async def test_update_and_remove_device(lan):
    ctx, hosts = lan
    res = await add(ctx, hosts, "g.test", AxeOSSim("gamma", seed=11, mac="AA:BB:CC:00:00:BB"))
    dev = await ctx.fleet.update(res.device.id, {"name": "Renamed", "tags": ["rack1"], "power_override_w": 18.5})
    assert dev.name == "Renamed" and dev.tags == ["rack1"] and dev.extra["power_override_w"] == 18.5
    with pytest.raises(ValueError, match="cannot change"):
        await ctx.fleet.update(res.device.id, {"driver": "evil"})
    with pytest.raises(ValueError, match="name cannot be empty"):
        await ctx.fleet.update(res.device.id, {"name": "  "})
    assert await ctx.fleet.remove(res.device.id)
    assert ctx.fleet.view(res.device.id) is None and await ctx.store.get_device(res.device.id) is None
    assert not await ctx.fleet.remove("nope")


def test_derive_status_rules():
    s = Settings()
    assert derive_status(Telemetry(hashrate_hs=1e12, uptime_s=5000), s)[0] == DeviceStatus.ONLINE
    st, why = derive_status(Telemetry(hashrate_hs=0, uptime_s=5000), s)
    assert st == DeviceStatus.DEGRADED and "Not hashing" in (why or "")
    assert derive_status(Telemetry(hashrate_hs=0, uptime_s=30), s)[0] == DeviceStatus.ONLINE  # still booting
    assert derive_status(Telemetry(hashrate_hs=1e12, pool_connected=False), s)[0] == DeviceStatus.DEGRADED
    assert derive_status(Telemetry(hashrate_hs=1e12, using_fallback=True), s)[0] == DeviceStatus.DEGRADED
    assert derive_status(Telemetry(hashrate_hs=1e12, temp_asic_c=90), s)[0] == DeviceStatus.DEGRADED
    assert derive_status(Telemetry(hashrate_hs=1e12, mining_paused=True), s)[0] == DeviceStatus.PAUSED
    assert derive_status(Telemetry(hashrate_hs=1e12, fault="VR fault"), s)[1] == "Fault reported: VR fault"
    assert derive_status(Telemetry(hashrate_hs=None, pool_connected=None), s)[0] == DeviceStatus.ONLINE


def test_summary_ignores_offline_devices():
    from bsmm.engine.fleet import DeviceRuntime
    from bsmm.models import Device

    def rt(status, hr, power):
        d = Device(id=f"d{hr}", name="x", driver="axeos", family="bitaxe", model="m", host=str(hr), port=80)
        r = DeviceRuntime(device=d, status=status, telemetry=Telemetry(hashrate_hs=hr, power_w=power, shares_accepted=10))
        r.hashrate_smooth = hr
        return r

    s = build_summary([rt(DeviceStatus.ONLINE, 1e12, 20), rt(DeviceStatus.OFFLINE, 5e12, 90)], Settings())
    assert s.devices_total == 2 and s.devices_offline == 1
    assert s.hashrate_hs == 1e12 and s.power_w == 20 and s.shares_accepted == 10


def test_performance_pct_compares_like_with_like_in_a_mixed_fleet():
    """Some firmwares (cgminer family) never report an expected hashrate. Their hashrate must not
    inflate 'actual vs expected', or a healthy fleet reads as 144% performance."""
    from bsmm.engine.fleet import DeviceRuntime
    from bsmm.models import Device

    def rt(name, hr, expected):
        d = Device(id=name, name=name, driver="axeos", family="bitaxe", model="m", host=name, port=80)
        r = DeviceRuntime(device=d, status=DeviceStatus.ONLINE, telemetry=Telemetry(hashrate_hs=hr, hashrate_expected_hs=expected))
        r.hashrate_smooth = hr
        return r

    s = build_summary([rt("a", 1.2e12, 1.0e12), rt("b", 0.9e12, 1.0e12), rt("no-expectation", 4e12, None)], Settings())
    assert s.hashrate_hs == 6.1e12  # the headline total still counts everything
    assert s.expected_hashrate_hs == 2.0e12
    assert s.performance_pct is not None and abs(s.performance_pct - 105.0) < 1e-6  # (1.2 + 0.9) / 2.0, not 6.1 / 2.0

    none_report = build_summary([rt("x", 1e12, None)], Settings())
    assert none_report.performance_pct is None and none_report.expected_hashrate_hs is None
