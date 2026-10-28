"""Offline regressions for telemetry, network facts and one-shot monitoring events."""
from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bsmm.drivers.cgminer import build_telemetry
from bsmm.engine.fleet import derive_status
from bsmm.engine.network import NetworkState, SourceHealth, _Poller
from bsmm.models import DeviceStatus, Source, Telemetry
from bsmm.settings import Settings
from bsmm.sources.base import BlockInfo, NetworkSnapshot, SourceUnreachable
from bsmm.sources.bitcoin_core import BitcoinCoreSource
from bsmm.storage.samples import Retention, telemetry_to_row


@pytest.mark.parametrize("family", ["antminer", "avalon", "cgminer"])
@pytest.mark.parametrize("current", [{"MHS 5s": 0}, {"MHS 1m": 0}, {"MHS 5s": 0, "MHS 1m": 0}])
def test_eng04_explicit_zero(family, current):
    t = build_telemetry({**current, "MHS av": 1_000_000, "Elapsed": 3600}, [], [], family=family)
    assert t.hashrate_hs == 0
    assert derive_status(t, Settings())[0] == DeviceStatus.DEGRADED


@pytest.mark.parametrize("current", [{}, {"MHS 5s": "bad"}, {"MHS 5s": "NaN"}])
def test_eng04_missing_invalid_falls_back(current):
    assert build_telemetry({**current, "MHS av": 1}, [], [], family="cgminer").hashrate_hs == 1e6


def test_eng04_avalon_zero_module_preferred():
    t = build_telemetry({"MHS 5s": 1_000_000}, [], [{"MM ID0": "GHSmm[0]"}], family="avalon")
    assert t.hashrate_hs == 0


async def test_eng05_failure_after_success_selects_fresh_fields(lan):
    ctx, _ = lan
    net = ctx.network
    src = Source(id="pool", kind="public_pool", name="pool")
    impl = SimpleNamespace(network=AsyncMock(side_effect=SourceUnreachable("synthetic outage")))
    p = _Poller(src, impl, snapshot=NetworkSnapshot(source="pool", difficulty=100, height=100, ts=time.time()-3600),
                health=SourceHealth(id="pool", kind="public_pool", name="pool", ok=True))
    fallback = _Poller(Source(id="fallback", kind="mempool_space", name="fallback"), impl,
                       snapshot=NetworkSnapshot(source="fallback", difficulty=200),
                       health=SourceHealth(id="fallback", kind="mempool_space", name="fallback", ok=True))
    net._pollers = {"pool": p, "fallback": fallback}
    await net._poll(p)
    await net._merge()
    assert net.state.difficulty == 200
    assert net.state.source == "fallback"
    # Unrelated fresh difficulty must not make the selected old height fresh.
    assert net.state.stale
    assert net.state.field_sources["height"].stale
    assert not net.state.field_sources["difficulty"].stale
    fallback.snapshot.height = 200
    await net._merge()
    assert not net.state.stale
    p.health.ok = True
    p.snapshot.ts = time.time()
    await net._merge()
    assert net.state.difficulty == 100  # healthy source precedence retained


async def test_eng06_device_only_loop_updates_and_ages(lan, monkeypatch):
    ctx, _ = lan
    net = ctx.network
    async def stop(_):
        net._running = False
    monkeypatch.setattr("bsmm.engine.network.asyncio.sleep", stop)
    for difficulty in (100, 200):
        net.set_device_snapshot(None, difficulty)
        net._running = True
        await net._loop()
        assert net.state.difficulty == difficulty
    merged_at = net.state.updated_at
    net.set_device_snapshot(None, 200, ts=net._device_snapshot.ts)
    net._running = True
    await net._loop()
    assert net.state.updated_at == merged_at  # no repeated writes for an identical observation
    net._device_snapshot.ts -= 601
    net._running = True
    await net._loop()
    assert net.state.stale


@pytest.mark.parametrize("next_tip", [False, True])
async def test_eng07_retry_incomplete_at_same_or_next_tip(lan, next_tip):
    ctx, _ = lan
    net = ctx.network
    net.watch_addresses = lambda: ["watched"]
    await ctx.store.kv_set("blocks.last_checked", 100)
    src = Source(id="core", kind="bitcoin_core", name="fake")
    core = BitcoinCoreSource(src, {}, ctx.http)
    core.block_info = AsyncMock(return_value=None)
    net._pollers = {"core": _Poller(src, core)}
    net._last_height = 100
    incomplete = NetworkState(height=101, recent_blocks=[BlockInfo(hash="h101", height=101, ts=1)])
    await net._after_merge(incomplete, 100, None)
    assert await ctx.store.kv_get("blocks.last_checked") == 100
    core.block_info = AsyncMock(side_effect=lambda h: BlockInfo(hash=f"h{h}", height=h, ts=1,
                                                                coinbase_addresses=["watched" if h == 101 else "other"]))
    tip = NetworkState(height=102 if next_tip else 101)
    await net._after_merge(tip, 101, None)
    await net._after_merge(tip, tip.height, None)
    assert await ctx.store.db.scalar("SELECT COUNT(*) FROM blocks_found") == 1
    assert len(await ctx.store.list_events(types=["block_found"])) == 1
    assert await ctx.store.kv_get("blocks.last_checked") == tip.height


async def test_eng08_null_weights_across_all_tiers(lan):
    ctx, _ = lan
    samples = ctx.store.samples
    rows = [telemetry_to_row("d", Telemetry(ts=3600, hashrate_hs=100, power_w=10)),
            telemetry_to_row("d", Telemetry(ts=3660, hashrate_hs=200, power_w=20))]
    rows += [telemetry_to_row("d", Telemetry(ts=3600+i*10, online=False, power_w=30)) for i in range(1, 6)]
    await samples.write(rows)
    for table in ("samples_1h", "samples_1d"):
        assert await ctx.store.db.scalar(f"SELECT hashrate_hs FROM {table}") == 150
        assert await ctx.store.db.scalar(f"SELECT power_w FROM {table}") == pytest.approx(180/7)
    hist = await samples.history(metrics=["hashrate_hs"], start=3600, end=3600+3*3600, step=3600)
    assert hist.series["hashrate_hs"][0] == 150


@pytest.mark.parametrize(("age_days", "expected"), [(3, "samples_1m"), (100, "samples_1h"), (800, "samples_1d")])
async def test_eng09_retained_short_window(lan, age_days, expected):
    ctx, _ = lan
    start = 86400
    await ctx.store.samples.write([telemetry_to_row("d", Telemetry(ts=start, hashrate_hs=100))])
    await ctx.store.samples.prune(Retention(), now=start+age_days*86400)
    hist = await ctx.store.samples.history(metrics=["hashrate_hs"], start=start, end=start+120)
    assert hist.source == expected
    assert hist.series["hashrate_hs"][0] == 100


@pytest.mark.parametrize("kind", ["new_best_share", "device_restarted"])
@pytest.mark.parametrize("scope", [{"device_ids": ["allowed"]}, {"tags": ["selected"]}])
async def test_eng10_event_scope_before_cooldown(lan, kind, scope):
    ctx, _ = lan
    from bsmm.models import DeviceView
    devices = [DeviceView(id="allowed", name="allowed", driver="sim", family="sim", model="sim", host="test", port=80, tags=["selected"])]
    ctx.fleet.views = lambda: devices
    ctx.alerts.notifier.dispatch = AsyncMock(return_value=[])
    await ctx.alerts.create_rule({"kind": kind, "scope": scope, "cooldown_s": 600})
    await ctx.alerts.handle_event({"type": kind, "device_id": "outside", "title": "excluded"})
    assert ctx.alerts.notifier.dispatch.call_count == 0
    assert not ctx.alerts._event_last
    await ctx.alerts.handle_event({"type": kind, "device_id": "allowed", "title": "included"})
    assert ctx.alerts.notifier.dispatch.call_count == 1
    await ctx.alerts.handle_event({"type": kind, "device_id": "allowed", "title": "cooldown"})
    assert ctx.alerts.notifier.dispatch.call_count == 1


@pytest.mark.parametrize("bad", ["NaN", "Infinity", "-Infinity"])
async def test_eng16_create_update_reject_nonfinite(api, bad):
    client, ctx, _ = api
    base = "/api/v1/alerts/rules"
    response = await client.post(base, json={"kind": "temp_high", "params": {"asic_c": bad}})
    assert response.status_code == 400
    rule = await ctx.alerts.create_rule({"kind": "temp_high", "params": {"asic_c": 75}})
    response = await client.patch(f"{base}/{rule.id}", json={"params": {"asic_c": bad}})
    assert response.status_code == 400
    assert (await ctx.store.get_rule(rule.id)).params["asic_c"] == 75
    for cooldown in (True, False):
        with pytest.raises(ValueError):
            await ctx.alerts.update_rule(rule.id, {"cooldown_s": bad} if cooldown else {"params": {"for_s": bad}})


async def test_eng15_overflow_replays_persisted_events(lan):
    ctx, _ = lan
    entered, release, delivered = asyncio.Event(), asyncio.Event(), asyncio.Event()
    seen = []
    async def dispatch(n, ids=None):
        seen.append(n.title)
        if n.title == "blocking":
            entered.set()
            await release.wait()
        if n.title == "critical":
            delivered.set()
        return []
    ctx.alerts.notifier.dispatch = dispatch
    await ctx.alerts.create_rule({"kind": "block_found", "cooldown_s": 0})
    ctx.alerts._running = True
    task = asyncio.create_task(ctx.alerts._event_loop())
    try:
        # Let the consumer establish its initial persisted cursor/subscription.
        for _ in range(100):
            if ctx.bus._subs:
                break
            await asyncio.sleep(0.001)
        await ctx.events.emit("block_found", "blocking")
        await asyncio.wait_for(entered.wait(), 2)
        await ctx.events.emit("block_found", "critical")
        for i in range(513):
            await ctx.events.emit("device_added", f"noise {i}")
        release.set()
        await asyncio.wait_for(delivered.wait(), 3)
        assert seen == ["blocking", "critical"]
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
