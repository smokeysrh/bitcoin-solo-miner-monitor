"""Issue #32: /metrics must not report unknown, disabled or silent miners as up, nor retained
readings as fresh samples."""

from __future__ import annotations

import time

from bsmm.models import DeviceStatus

from .test_api import add_miner

INSTANT_METRICS = (
    "bsmm_device_hashrate_hashes_per_second",
    "bsmm_device_power_watts",
    "bsmm_device_temperature_asic_celsius",
    "bsmm_device_fan_rpm",
    "bsmm_device_frequency_mhz",
)
STALE_AGE_S = 3600.0


def _value(text: str, name: str, device_id: str) -> float | None:
    for line in text.splitlines():
        if line.startswith(f'{name}{{device="{device_id}"'):
            return float(line.rsplit(" ", 1)[1])
    return None


async def _metrics(c) -> str:
    return (await c.get("/metrics")).text


def _assert_no_instant_samples(text: str, device_id: str) -> None:
    for name in INSTANT_METRICS:
        assert _value(text, name, device_id) is None, name


async def test_fresh_online_miner_is_up_with_samples(api):
    c, ctx, hosts = api
    dev = await add_miner(c, ctx, hosts)
    text = await _metrics(c)
    assert _value(text, "bsmm_device_up", dev.id) == 1
    assert _value(text, "bsmm_device_enabled", dev.id) == 1
    assert _value(text, "bsmm_device_power_watts", dev.id) is not None
    assert _value(text, "bsmm_device_temperature_asic_celsius", dev.id) is not None
    observed = ctx.fleet.runtimes[dev.id].telemetry.ts
    assert _value(text, "bsmm_device_last_observation_timestamp_seconds", dev.id) == float(f"{observed:.10g}")


async def test_never_polled_miner_is_not_up(api):
    c, ctx, hosts = api
    from bsmm.sim.axeos import AxeOSSim

    hosts["gamma.test"] = AxeOSSim("gamma", seed=1, mac="AA:BB:CC:00:00:11").app()
    dev = (await ctx.fleet.add_by_host("gamma.test", drivers=["axeos"])).device
    assert ctx.fleet.runtimes[dev.id].status == DeviceStatus.UNKNOWN
    text = await _metrics(c)
    assert _value(text, "bsmm_device_up", dev.id) == 0
    assert _value(text, "bsmm_device_last_observation_timestamp_seconds", dev.id) is None
    _assert_no_instant_samples(text, dev.id)


async def test_reenabled_unknown_miner_with_retained_readings_is_not_up(api):
    c, ctx, hosts = api
    dev = await add_miner(c, ctx, hosts)
    ctx.fleet.runtimes[dev.id].status = DeviceStatus.UNKNOWN  # what re-enabling a miner does until its first poll
    text = await _metrics(c)
    assert _value(text, "bsmm_device_up", dev.id) == 0
    _assert_no_instant_samples(text, dev.id)


async def test_disabled_miner_is_not_up_and_reports_disabled(api):
    c, ctx, hosts = api
    dev = await add_miner(c, ctx, hosts)
    await ctx.fleet.update(dev.id, {"enabled": False})
    assert ctx.fleet.runtimes[dev.id].status == DeviceStatus.DISABLED
    text = await _metrics(c)
    assert _value(text, "bsmm_device_up", dev.id) == 0
    assert _value(text, "bsmm_device_enabled", dev.id) == 0
    _assert_no_instant_samples(text, dev.id)


async def test_offline_miner_is_not_up_and_has_no_instant_samples(api):
    c, ctx, hosts = api
    dev = await add_miner(c, ctx, hosts)
    ctx.fleet.runtimes[dev.id].status = DeviceStatus.OFFLINE
    text = await _metrics(c)
    assert _value(text, "bsmm_device_up", dev.id) == 0
    _assert_no_instant_samples(text, dev.id)


async def test_degraded_miner_that_answered_recently_is_still_up(api):
    c, ctx, hosts = api
    dev = await add_miner(c, ctx, hosts)
    ctx.fleet.runtimes[dev.id].status = DeviceStatus.DEGRADED
    text = await _metrics(c)
    assert _value(text, "bsmm_device_up", dev.id) == 1
    assert _value(text, "bsmm_device_power_watts", dev.id) is not None


async def test_stale_last_success_is_not_up_and_not_a_current_sample(api):
    c, ctx, hosts = api
    dev = await add_miner(c, ctx, hosts)
    telemetry = ctx.fleet.runtimes[dev.id].telemetry
    telemetry.ts = time.time() - STALE_AGE_S
    assert ctx.fleet.runtimes[dev.id].status == DeviceStatus.ONLINE
    text = await _metrics(c)
    assert _value(text, "bsmm_device_up", dev.id) == 0
    _assert_no_instant_samples(text, dev.id)
    # the age of the last observation stays visible, and cumulative counters stay historical
    assert _value(text, "bsmm_device_last_observation_timestamp_seconds", dev.id) == float(f"{telemetry.ts:.10g}")
    assert _value(text, "bsmm_device_shares_accepted_total", dev.id) is not None


async def test_up_help_matches_emitted_semantics(api):
    c, ctx, hosts = api
    await add_miner(c, ctx, hosts)
    text = await _metrics(c)
    help_line = next(line for line in text.splitlines() if line.startswith("# HELP bsmm_device_up "))
    assert "recent" in help_line
