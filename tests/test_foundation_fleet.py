"""Foundation repairs exercised through fleet and API callers, using only simulators."""
import asyncio
import sqlite3

import pytest

from bsmm.drivers.base import DriverError
from bsmm.models import DeviceInfo, ProbeResult, Telemetry
from bsmm.sim.axeos import AxeOSSim
from bsmm.storage.samples import telemetry_to_row

from .test_fleet import add


async def miner(ctx, hosts, host="miner.test", mac="AA:BB:CC:00:00:01"):
    sim = AxeOSSim("gamma", seed=1, mac=mac)
    result = await add(ctx, hosts, host, sim)
    return result.device.id, sim


@pytest.mark.parametrize("alternate", [False, True])
async def test_conflicting_identity_cannot_be_adopted(lan, alternate):
    ctx, hosts = lan
    did, sim = await miner(ctx, hosts)
    endpoint = "miner.test"
    if alternate:
        endpoint = "alternate.test"
        hosts[endpoint] = sim.app()
        assert not (await ctx.fleet.add_by_host(endpoint, drivers=["axeos"])).created
    other = AxeOSSim("gamma", seed=2, mac="AA:BB:CC:00:00:02")
    # Replace the existing transport app's identity, not its cached ASGI transport.
    sim.mac = other.mac
    with pytest.raises((DriverError, ValueError), match="identity"):
        await ctx.fleet.add_by_host(endpoint, drivers=["axeos"])
    assert len(ctx.fleet.views()) == 1
    assert (await ctx.store.get_device(did)).mac == "AA:BB:CC:00:00:01"


async def test_unavailable_identity_keeps_endpoint_compatibility(lan):
    ctx, _ = lan
    info = DeviceInfo(driver="cgminer", family="cgminer", model="unknown", host="offline.test", port=4028)
    first = await ctx.fleet.add_from_probe(ProbeResult(info=info))
    second = await ctx.fleet.add_from_probe(ProbeResult(info=info))
    assert first.device.id == second.device.id and not second.created


async def test_replaced_identity_cannot_poll(lan):
    ctx, hosts = lan
    did, sim = await miner(ctx, hosts)
    await ctx.fleet.poll_now(did)
    ctx.fleet._pending[0]["ts"] = 3600  # distinct from the later offline sample's second
    await ctx.fleet._flush_samples()
    count = await ctx.store.db.scalar("SELECT COUNT(*) FROM samples")
    sim.mac = "AA:BB:CC:00:00:02"
    for _ in range(3):
        await ctx.fleet.poll_now(did)
    assert ctx.fleet.view(did).status != "online"
    assert ctx.fleet.view(did).last_error and "identity" in ctx.fleet.view(did).last_error
    await ctx.fleet._flush_samples()
    assert await ctx.store.db.scalar("SELECT COUNT(*) FROM samples WHERE hashrate_hs IS NOT NULL") == count


@pytest.mark.parametrize("patch", [{"name": None}, {"name": "  "}, {"tags": None}, {"enabled": None}, {"host": None}])
async def test_rejected_patch_preserves_runtime_and_get(api, patch):
    client, ctx, hosts = api
    did, _ = await miner(ctx, hosts)
    before = (await ctx.store.get_device(did)).model_dump()
    response = await client.patch(f"/api/v1/devices/{did}", json=patch)
    assert response.status_code in (400, 422)
    assert ctx.fleet.runtimes[did].device.model_dump() == before
    assert (await ctx.store.get_device(did)).model_dump() == before
    assert (await client.get("/api/v1/devices")).status_code == 200


async def test_duplicate_endpoint_and_db_failure_preserve_driver(api, monkeypatch):
    client, ctx, hosts = api
    did, _ = await miner(ctx, hosts)
    await miner(ctx, hosts, "other.test", "AA:BB:CC:00:00:02")
    rt = ctx.fleet.runtimes[did]
    await ctx.fleet.poll_now(did)
    old, driver = rt.device.model_dump(), rt.driver
    response = await client.patch(f"/api/v1/devices/{did}", json={"host": "other.test"})
    assert response.status_code in (400, 409, 422)
    assert rt.device.model_dump() == old and rt.driver is driver

    async def fail(*args, **kwargs):
        raise sqlite3.OperationalError("simulated disk failure")

    monkeypatch.setattr(ctx.store, "save_device", fail)
    with pytest.raises(sqlite3.OperationalError):
        await ctx.fleet.update(did, {"name": "changed", "power_override_w": 40})
    assert rt.device.model_dump() == old and rt.driver is driver
    assert (await client.get("/api/v1/devices")).status_code == 200


@pytest.mark.parametrize("keep_history", [False, True])
@pytest.mark.parametrize("inflight", [False, True])
async def test_remove_cannot_resurrect_samples(lan, monkeypatch, keep_history, inflight):
    ctx, hosts = lan
    did, _ = await miner(ctx, hosts)
    ctx.fleet._pending.append(telemetry_to_row(did, Telemetry(ts=3600, hashrate_hs=100)))
    entered, release = asyncio.Event(), asyncio.Event()
    original = ctx.store.samples.write

    async def held(rows):
        entered.set()
        await release.wait()
        await original(rows)

    writer = None
    if inflight:
        monkeypatch.setattr(ctx.store.samples, "write", held)
        writer = asyncio.create_task(ctx.fleet._flush_samples())
        await entered.wait()
    removal = asyncio.create_task(ctx.fleet.remove(did, keep_history=keep_history))
    await asyncio.sleep(0)
    release.set()
    assert await asyncio.wait_for(removal, 2)
    if writer:
        await writer
    await ctx.fleet._flush_samples()
    assert await ctx.store.get_device(did) is None
    for table in ("samples", "samples_1m", "samples_1h", "samples_1d"):
        assert await ctx.store.db.scalar(f"SELECT COUNT(*) FROM {table} WHERE device_id=?", (did,)) == int(keep_history)


@pytest.mark.parametrize("boundary", ["before", "raw", "rollup"])
async def test_stop_preserves_owned_batch_once(lan, monkeypatch, boundary):
    ctx, hosts = lan
    did, _ = await miner(ctx, hosts)
    ctx.fleet._pending.append(telemetry_to_row(did, Telemetry(ts=3600, hashrate_hs=100)))
    entered, release = asyncio.Event(), asyncio.Event()
    original_write = ctx.store.samples.write
    original_rollup = ctx.store.samples.rollup_window

    async def held_write(rows):
        entered.set()
        await release.wait()
        await original_write(rows)

    async def held_rollup(*args):
        if boundary == "rollup":
            await original_rollup(*args)
        entered.set()
        await release.wait()
        if boundary == "raw":
            await original_rollup(*args)

    if boundary == "before":
        monkeypatch.setattr(ctx.store.samples, "write", held_write)
    else:
        monkeypatch.setattr(ctx.store.samples, "rollup_window", held_rollup)
    task = asyncio.create_task(ctx.fleet._flush_samples())
    ctx.fleet._bg = [task]
    await entered.wait()
    stopping = asyncio.create_task(ctx.fleet.stop())
    # Let actual stop deliver cancellation before permitting persistence.
    while not task.cancelling() and not task.done():
        await asyncio.sleep(0)
    release.set()
    await asyncio.wait_for(stopping, 2)
    assert not ctx.fleet._pending
    assert await ctx.store.db.scalar("SELECT COUNT(*) FROM samples") == 1
    for table in ("samples_1m", "samples_1h", "samples_1d"):
        assert await ctx.store.db.scalar(f"SELECT SUM(n) FROM {table}") == 1
