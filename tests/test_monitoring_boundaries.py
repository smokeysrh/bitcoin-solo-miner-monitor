"""Cancellation, migration and caller-boundary controls for the monitoring repairs."""
import asyncio
import sqlite3
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bsmm.engine.alerts import RULE_SPECS, AlertEngine, EvalContext, eval_temp_high, validate_rule
from bsmm.engine.network import NetworkState, _Poller
from bsmm.models import AlertRule, DeviceStatus, DeviceView, FleetSummary, Source, Telemetry
from bsmm.sources.base import BlockInfo, SourceUnreachable
from bsmm.sources.bitcoin_core import BitcoinCoreSource
from bsmm.storage.db import MIGRATIONS, Database
from bsmm.storage.samples import Retention, SampleStore, telemetry_to_row


async def test_eng06_feeder_preserves_observation_age_and_pair(lan, monkeypatch):
    ctx, _ = lan
    now = time.time()
    older = Telemetry(ts=now-1000, network_difficulty=100, block_height=999)
    newer = Telemetry(ts=now-30, network_difficulty=200, block_height=100)
    ctx.fleet.runtimes = {
        "a": SimpleNamespace(telemetry=older, status=DeviceStatus.ONLINE),
        "b": SimpleNamespace(telemetry=newer, status=DeviceStatus.ONLINE),
    }
    calls = 0
    async def one_cycle(_):
        nonlocal calls
        calls += 1
        if calls > 1:
            raise asyncio.CancelledError
    monkeypatch.setattr("bsmm.context.asyncio.sleep", one_cycle)
    with pytest.raises(asyncio.CancelledError):
        await ctx._feed_device_network_facts()
    snap = ctx.network._device_snapshot
    assert (snap.height, snap.difficulty, snap.ts) == (100, 200, now-30)
    # Offline telemetry is retained in Fleet for display, not refreshed as a new network fact.
    for rt in ctx.fleet.runtimes.values():
        rt.status = DeviceStatus.OFFLINE
        rt.telemetry.ts = now
    calls = 0
    with pytest.raises(asyncio.CancelledError):
        await ctx._feed_device_network_facts()
    assert ctx.network._device_snapshot.ts == now-30
    ctx.fleet.runtimes.clear()


@pytest.mark.parametrize("failure", ["getblock", "getrawtransaction", "incomplete"])
async def test_eng07_real_core_details_retry_without_caching_headers(lan, failure):
    ctx, _ = lan
    src = Source(id="core", kind="bitcoin_core", name="fake", url="http://127.0.0.1:1")
    core = BitcoinCoreSource(src, {}, ctx.http)
    recovered = False
    async def rpc(method, params):
        if not recovered and method == failure:
            raise SourceUnreachable("synthetic transient failure")
        if method == "getblockhash":
            return "hash101"
        if method == "getblock":
            return {"tx": ["coinbase"], "time": 1}
        if method == "getrawtransaction":
            return {} if not recovered and failure == "incomplete" else {"vout": [{"value": 3.125, "scriptPubKey": {"address": "watched"}}]}
        raise AssertionError(method)
    core.rpc.call = rpc
    ctx.network._pollers = {"core": _Poller(src, core)}
    ctx.network.watch_addresses = lambda: ["watched"]
    await ctx.store.kv_set("blocks.last_checked", 100)
    st = NetworkState(height=101, recent_blocks=[BlockInfo(hash="hash101", height=101, ts=1)])
    await ctx.network._check_blocks(st, 100)
    assert await ctx.store.kv_get("blocks.last_checked") == 100
    assert core._block_cache == {}
    recovered = True
    await ctx.network._check_blocks(st, 100)
    await ctx.network._check_blocks(st, 100)
    assert len(await ctx.store.list_blocks_found()) == 1
    assert len(await ctx.store.list_events(types=["block_found"])) == 1


async def test_eng07_cancellation_keeps_marker_and_addressless_complete_advances(lan):
    ctx, _ = lan
    src = Source(id="core", kind="bitcoin_core", name="fake")
    core = BitcoinCoreSource(src, {}, ctx.http)
    core.block_info = AsyncMock(side_effect=asyncio.CancelledError)
    ctx.network._pollers = {"core": _Poller(src, core)}
    await ctx.store.kv_set("blocks.last_checked", 100)
    with pytest.raises(asyncio.CancelledError):
        await ctx.network._check_blocks(NetworkState(height=101), 100)
    assert await ctx.store.kv_get("blocks.last_checked") == 100
    core.block_info = AsyncMock(return_value=BlockInfo(hash="h101", height=101, ts=1, coinbase_complete=True))
    await ctx.network._check_blocks(NetworkState(height=101), 100)
    assert await ctx.store.kv_get("blocks.last_checked") == 101
    assert await ctx.store.list_blocks_found() == []


async def test_eng07_concurrent_checks_record_once(lan):
    ctx, _ = lan
    ctx.network.watch_addresses = lambda: ["watched"]
    await ctx.store.kv_set("blocks.last_checked", 100)
    st = NetworkState(height=101, recent_blocks=[BlockInfo(hash="h101", height=101, ts=1, coinbase_addresses=["watched"])])
    await asyncio.gather(ctx.network._check_blocks(st, 100), ctx.network._check_blocks(st, 100))
    assert len(await ctx.store.list_blocks_found()) == 1
    assert len(await ctx.store.list_events(types=["block_found"])) == 1


async def test_eng06_update_during_merge_is_not_lost(lan):
    ctx, _ = lan
    net = ctx.network
    net.set_device_snapshot(None, 100)
    # Hold the real merge at its existing state lock while a new reading arrives.
    await net._lock.acquire()
    task = asyncio.create_task(net._merge())
    try:
        async with asyncio.timeout(2):
            while net._device_dirty:
                await asyncio.sleep(0)
        net.set_device_snapshot(None, 200)
    finally:
        net._lock.release()
    await task
    assert net._device_dirty
    await net._merge()
    assert net.state.difficulty == 200
    assert not net._device_dirty


async def test_eng08_upgrade_keeps_legacy_and_discloses_unknown_weights(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as old:
        old.executescript(MIGRATIONS[0][1])
        old.execute("PRAGMA user_version=1")
        old.execute("INSERT INTO samples_1m(device_id,bucket,n,hashrate_hs) VALUES ('d',3600,6,100)")
        old.execute("INSERT INTO samples_1m(device_id,bucket,n,hashrate_hs) VALUES ('d',3660,1,200)")
    db = Database(path)
    await db.connect()
    try:
        assert await db.schema_version() >= 2
        assert await db.scalar("SELECT SUM(n) FROM samples_1m") == 7
        assert await db.scalar("SELECT COUNT(hashrate_hs_n) FROM samples_1m") == 0
        samples = SampleStore(db)
        hist = await samples.history(metrics=["hashrate_hs"], start=3600, end=10801, step=3600)
        assert hist.series["hashrate_hs"][0] == pytest.approx(800/7)
        assert "approximate" in hist.as_dict()["warnings"][0]
        # Newly observed metric counts never borrow the total row count.
        await samples.write([telemetry_to_row("new", Telemetry(ts=3600, hashrate_hs=100)),
                             telemetry_to_row("new", Telemetry(ts=3610, online=False))])
        assert await db.scalar("SELECT hashrate_hs_n FROM samples_1m WHERE device_id='new'") == 1
        hist = await samples.history(metrics=["hashrate_hs"], start=3600, end=10801, device_ids=["new"])
        assert hist.warnings == []
    finally:
        await db.close()
    await db.connect()  # migration is restart-safe
    await db.close()


async def test_eng08_partial_rebuild_does_not_replace_retained_bucket(lan):
    ctx, _ = lan
    await ctx.store.samples.write([telemetry_to_row("d", Telemetry(ts=3600, hashrate_hs=100)),
                                   telemetry_to_row("d", Telemetry(ts=3660, hashrate_hs=200))])
    await ctx.store.db.execute("DELETE FROM samples WHERE ts=3600")
    await ctx.store.samples.rebuild_rollups()
    assert await ctx.store.db.scalar("SELECT hashrate_hs FROM samples_1h") == 150
    assert await ctx.store.db.scalar("SELECT hashrate_hs_n FROM samples_1h") == 2


async def test_eng09_mixed_retention_window_and_device_filter(api):
    client, ctx, _ = api
    now = 10*86400
    times = [now-3*86400, now-86400]
    await ctx.store.samples.write([telemetry_to_row("d", Telemetry(ts=t, hashrate_hs=100)) for t in times])
    await ctx.store.samples.prune(Retention(), now=now)
    hist = await ctx.store.samples.history(metrics=["hashrate_hs"], start=times[0], end=times[1], device_ids=["d"])
    assert hist.source == "samples_1m"
    assert hist.series["hashrate_hs"][0] == hist.series["hashrate_hs"][-1] == 100
    response = await client.get("/api/v1/fleet/history", params={"start": times[0], "end": times[0]+120, "metrics": "hashrate_hs"})
    assert response.status_code == 200
    assert response.json()["source"] == "samples_1m"
    empty = await ctx.store.samples.history(metrics=["hashrate_hs"], start=times[0], end=times[0]+120, device_ids=["other"])
    assert all(v is None for v in empty.series["hashrate_hs"])


async def test_eng09_short_window_crossing_pruning_inside_same_minute(lan):
    ctx, _ = lan
    await ctx.store.samples.write([telemetry_to_row("d", Telemetry(ts=3601, hashrate_hs=100)),
                                   telemetry_to_row("d", Telemetry(ts=3630, hashrate_hs=200))])
    full = await ctx.store.samples.history(metrics=["hashrate_hs"], start=3600, end=3650, device_ids=["d"])
    assert full.source == "samples"  # mere native-bucket alignment is not evidence of pruning
    # The retained minute contains both readings, but the first raw sample was pruned.
    await ctx.store.db.execute("DELETE FROM samples WHERE ts=3601")
    hist = await ctx.store.samples.history(metrics=["hashrate_hs"], start=3601, end=3650, device_ids=["d"])
    assert hist.source == "samples_1m"
    assert hist.series["hashrate_hs"][0] == 150


async def test_eng10_global_event_requires_unrestricted_scope(lan):
    ctx, _ = lan
    ctx.alerts.notifier.dispatch = AsyncMock(return_value=[])
    await ctx.alerts.create_rule({"kind": "block_found", "scope": {"tags": ["only"]}})
    await ctx.alerts.handle_event({"type": "block_found", "title": "global"})
    assert ctx.alerts.notifier.dispatch.call_count == 0
    await ctx.alerts.create_rule({"kind": "block_found", "scope": {"all": True}})
    await ctx.alerts.handle_event({"type": "block_found", "title": "global"})
    assert ctx.alerts.notifier.dispatch.call_count == 1


@pytest.mark.parametrize("bad", ["NaN", "Infinity", "-Infinity"])
def test_eng16_every_numeric_parameter_rejects_nonfinite(bad):
    for spec in RULE_SPECS.values():
        for param in spec.params:
            rule = AlertRule(id="r", name="r", kind=spec.kind, params={param.name: bad})
            with pytest.raises(ValueError):
                validate_rule(rule)
            for value in (param.min, param.max):
                if value is not None:
                    rule.params = {param.name: str(value)}
                    validate_rule(rule)
                    assert rule.params[param.name] == value


async def test_eng16_rejected_update_preserves_hot_detection(lan):
    ctx, _ = lan
    rule = await ctx.alerts.create_rule({"kind": "temp_high", "params": {"asic_c": 75}})
    with pytest.raises(ValueError):
        await ctx.alerts.update_rule(rule.id, {"params": {"asic_c": "NaN"}})
    hot = DeviceView(id="hot", name="hot", driver="sim", family="sim", model="sim", host="test", port=80,
                     status="online", telemetry=Telemetry(temp_asic_c=100))
    ev = EvalContext(time.time(), [hot], FleetSummary(), ctx.network.state, ctx.settings.current, {}, None)
    assert eval_temp_high(await ctx.store.get_rule(rule.id), ev)
    hot.telemetry.temp_asic_c = 40
    assert not eval_temp_high(await ctx.store.get_rule(rule.id), ev)


async def wait_for_cursor(store, event_id):
    async with asyncio.timeout(3):
        while await store.kv_get("alerts.event_cursor", 0) < event_id:
            await asyncio.sleep(0.005)


async def test_eng15_cancel_restart_and_successful_replay_dedup(lan):
    ctx, _ = lan
    await ctx.alerts.create_rule({"kind": "block_found", "cooldown_s": 0})
    await ctx.store.kv_set("alerts.event_cursor", 0)
    ev = await ctx.events.emit("block_found", "critical")
    entered = asyncio.Event()
    async def blocked(n, ids=None):
        entered.set()
        await asyncio.Event().wait()
    ctx.alerts.notifier.dispatch = blocked
    task = asyncio.create_task(ctx.alerts._event_loop())
    await asyncio.wait_for(entered.wait(), 2)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    assert await ctx.store.kv_get("alerts.event_cursor") == 0
    assert ctx.bus.subscriber_count == 0
    sink = SimpleNamespace(dispatch=AsyncMock(return_value=[]))
    engine = AlertEngine(ctx.store, ctx.settings, ctx.bus, ctx.fleet, ctx.network, sink)
    task = asyncio.create_task(engine._event_loop())
    try:
        await wait_for_cursor(ctx.store, ev.id)
        assert sink.dispatch.call_count == 1
        # Even if a crash lost the global cursor write, the per-rule receipt prevents a second send.
        await ctx.store.kv_set("alerts.event_cursor", 0)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    task = asyncio.create_task(engine._event_loop())
    try:
        await wait_for_cursor(ctx.store, ev.id)
        assert sink.dispatch.call_count == 1
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
