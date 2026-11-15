"""Cancellation and queued lifecycle boundaries; no external I/O."""
import asyncio
import sqlite3

import pytest

from bsmm.drivers.base import DriverError
from bsmm.models import Telemetry
from bsmm.storage.samples import telemetry_to_row

from .test_foundation_fleet import miner


@pytest.mark.parametrize("boundary", ["before_commit", "after_commit"])
async def test_cancelled_update_finishes_db_runtime_handoff(lan, monkeypatch, boundary):
    ctx, hosts = lan
    did, _ = await miner(ctx, hosts)
    rt = ctx.fleet.runtimes[did]
    driver = ctx.fleet._ensure_driver(rt)
    entered, release = asyncio.Event(), asyncio.Event()
    original = ctx.store.save_device

    async def held(dev, **kwargs):
        if boundary == "after_commit":
            await original(dev, **kwargs)
        entered.set()
        await release.wait()
        if boundary == "before_commit":
            await original(dev, **kwargs)

    monkeypatch.setattr(ctx.store, "save_device", held)
    task = asyncio.create_task(ctx.fleet.update(did, {"name": "updated"}))
    await entered.wait()
    task.cancel()
    await asyncio.sleep(0)
    task.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert rt.device.name == (await ctx.store.get_device(did)).name == "updated"
    assert rt.driver is driver


@pytest.mark.parametrize("keep_history", [False, True])
async def test_remove_waits_for_explicit_poll(lan, monkeypatch, keep_history):
    ctx, hosts = lan
    did, _ = await miner(ctx, hosts)
    driver = ctx.fleet._ensure_driver(ctx.fleet.runtimes[did])
    entered, release = asyncio.Event(), asyncio.Event()
    original = driver.poll

    async def held():
        entered.set()
        await release.wait()
        return await original()

    monkeypatch.setattr(driver, "poll", held)
    polling = asyncio.create_task(ctx.fleet.poll_now(did))
    await entered.wait()
    removal = asyncio.create_task(ctx.fleet.remove(did, keep_history=keep_history))
    await asyncio.sleep(0)
    release.set()
    await polling
    await removal
    await ctx.fleet._flush_samples()
    assert await ctx.store.db.scalar("SELECT COUNT(*) FROM samples") == int(keep_history)


@pytest.mark.parametrize("keep_history", [False, True])
async def test_cancelled_remove_finishes_history_decision(lan, monkeypatch, keep_history):
    ctx, hosts = lan
    did, _ = await miner(ctx, hosts)
    ctx.fleet._pending.append(telemetry_to_row(did, Telemetry(ts=3600, hashrate_hs=100)))
    entered, release = asyncio.Event(), asyncio.Event()
    original = ctx.store.delete_device

    async def held(*args, **kwargs):
        result = await original(*args, **kwargs)
        entered.set()
        await release.wait()
        return result

    monkeypatch.setattr(ctx.store, "delete_device", held)
    task = asyncio.create_task(ctx.fleet.remove(did, keep_history=keep_history))
    await entered.wait()
    task.cancel()
    await asyncio.sleep(0)
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    await ctx.fleet._flush_samples()
    assert did not in ctx.fleet.runtimes
    assert await ctx.store.get_device(did) is None
    for table in ("samples", "samples_1m", "samples_1h", "samples_1d"):
        assert await ctx.store.db.scalar(f"SELECT COUNT(*) FROM {table}") == int(keep_history)


async def test_stop_cancelled_at_sample_commit_finishes_once(lan, monkeypatch):
    ctx, hosts = lan
    did, _ = await miner(ctx, hosts)
    ctx.fleet._pending.append(telemetry_to_row(did, Telemetry(ts=3600, hashrate_hs=100)))
    entered, release = asyncio.Event(), asyncio.Event()
    original = ctx.store.db.conn.commit

    async def held():
        await original()
        entered.set()
        await release.wait()

    monkeypatch.setattr(ctx.store.db.conn, "commit", held)
    task = asyncio.create_task(ctx.fleet.stop())
    await entered.wait()
    task.cancel()
    await asyncio.sleep(0)
    task.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not ctx.fleet._pending
    assert await ctx.store.db.scalar("SELECT COUNT(*) FROM samples") == 1
    for table in ("samples_1m", "samples_1h", "samples_1d"):
        assert await ctx.store.db.scalar(f"SELECT SUM(n) FROM {table}") == 1


async def test_failed_rollup_retains_batch_and_retry_is_atomic(lan, monkeypatch):
    ctx, hosts = lan
    did, _ = await miner(ctx, hosts)
    ctx.fleet._pending.append(telemetry_to_row(did, Telemetry(ts=3600, hashrate_hs=100)))
    original = ctx.store.samples.rollup_window

    async def fail(*args):
        await original(*args)
        raise sqlite3.OperationalError("simulated rollup failure")

    monkeypatch.setattr(ctx.store.samples, "rollup_window", fail)
    with pytest.raises(sqlite3.OperationalError):
        await ctx.fleet._flush_samples()
    assert len(ctx.fleet._pending) == 1
    for table in ("samples", "samples_1m", "samples_1h", "samples_1d"):
        assert await ctx.store.db.scalar(f"SELECT COUNT(*) FROM {table}") == 0
    monkeypatch.setattr(ctx.store.samples, "rollup_window", original)
    await ctx.fleet._flush_samples()
    assert not ctx.fleet._pending
    for table in ("samples_1m", "samples_1h", "samples_1d"):
        assert await ctx.store.db.scalar(f"SELECT SUM(n) FROM {table}") == 1


async def test_known_mac_elsewhere_cannot_override_conflicting_endpoint(lan):
    ctx, hosts = lan
    _, first = await miner(ctx, hosts)
    await miner(ctx, hosts, "other.test", "AA:BB:CC:00:00:02")
    first.mac = "AA:BB:CC:00:00:02"
    with pytest.raises(DriverError, match="identity"):
        await ctx.fleet.add_by_host("miner.test", drivers=["axeos"])


async def test_missing_mac_payload_remains_compatible(lan, monkeypatch):
    ctx, hosts = lan
    did, sim = await miner(ctx, hosts)
    original = sim.info

    def without_mac():
        data = original()
        data.pop("macAddr", None)
        return data

    monkeypatch.setattr(sim, "info", without_mac)
    assert (await ctx.fleet.poll_now(did)).status == "online"


async def test_failed_delete_keeps_runtime_driver_and_buffer(lan, monkeypatch):
    ctx, hosts = lan
    did, _ = await miner(ctx, hosts)
    rt = ctx.fleet.runtimes[did]
    driver = ctx.fleet._ensure_driver(rt)
    ctx.fleet._pending.append(telemetry_to_row(did, Telemetry(ts=3600, hashrate_hs=100)))

    async def fail(*args, **kwargs):
        raise sqlite3.OperationalError("simulated delete failure")

    monkeypatch.setattr(ctx.store, "delete_device", fail)
    with pytest.raises(sqlite3.OperationalError):
        await ctx.fleet.remove(did)
    assert ctx.fleet.runtimes[did] is rt and rt.driver is driver
    assert not rt.removing and len(ctx.fleet._pending) == 1
    assert await ctx.store.get_device(did) is not None


async def test_alias_merge_keeps_edits_made_while_it_waited(lan, monkeypatch):
    ctx, hosts = lan
    did, sim = await miner(ctx, hosts)
    hosts["alias.test"] = sim.app()
    entered, release = asyncio.Event(), asyncio.Event()
    original = ctx.store.find_device

    async def held(info):
        result = await original(info)
        entered.set()
        await release.wait()
        return result

    monkeypatch.setattr(ctx.store, "find_device", held)
    merging = asyncio.create_task(ctx.fleet.add_by_host("alias.test", drivers=["axeos"]))
    await entered.wait()
    await ctx.fleet.update(did, {"notes": "kept", "name": "renamed"})
    release.set()
    result = await merging
    assert result.merged
    assert ctx.fleet.runtimes[did].device.name == "renamed"
    assert ctx.fleet.runtimes[did].device.notes == "kept"
    saved = await ctx.store.get_device(did)
    assert saved.notes == "kept" and saved.name == "renamed"
