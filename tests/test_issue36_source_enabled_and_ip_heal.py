"""Issue #36: a disabled source stays disabled and uncontacted, and automatic IP healing obeys the fleet's rules.

Everything here runs the real API app, the real fleet and the real discovery service over the in-process simulated
network from ``conftest``; only the TCP sweep and (to hold a scan open) the protocol probe are swapped.
"""

from __future__ import annotations

import asyncio
import contextlib
import sqlite3
from typing import Any

import pytest

import bsmm.engine.discovery as discovery_mod
from bsmm.drivers.registry import probe_host
from bsmm.models import DeviceStatus
from bsmm.sim.axeos import AxeOSSim

from .test_network_service import pool_routes, site

MAC = "AA:BB:CC:00:00:31"
OLD_HOST, NEW_HOST = "10.36.0.5", "10.36.0.77"
POOL_URL = "http://pool.test:2019"


# --- adding a source ---------------------------------------------------------------------------------------------------------------------------


class CountingApp:
    """Wraps an ASGI app and counts the HTTP requests it receives."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.requests = 0

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] == "http":
            self.requests += 1
        await self.inner(scope, receive, send)


async def test_a_source_added_disabled_is_saved_disabled_and_never_contacted(api):
    c, ctx, hosts = api
    pool = CountingApp(site(pool_routes()))
    hosts["pool.test"] = pool

    r = await c.post("/api/v1/sources", json={"kind": "public_pool", "url": POOL_URL, "enabled": False})

    assert r.status_code == 200, r.text
    source = r.json()["source"]
    assert source["enabled"] is False
    stored = await ctx.store.get_source(source["id"])
    assert stored is not None and stored.enabled is False
    assert source["id"] not in ctx.network._pollers
    assert pool.requests == 0  # staging a source makes no network request; POST /sources/test is the explicit way to try it


async def test_a_source_added_without_the_flag_is_still_enabled_and_polled(api):
    c, ctx, hosts = api
    hosts["pool.test"] = site(pool_routes())

    r = await c.post("/api/v1/sources", json={"kind": "public_pool", "url": POOL_URL})

    assert r.status_code == 200, r.text
    source = r.json()["source"]
    assert source["enabled"] is True
    assert source["id"] in ctx.network._pollers


# --- healing a miner that changed address ---------------------------------------------------------------------------------------------------


class HeldScan:
    """Lets a test pause the healing scan after it identified the miner, and act before the scan continues."""

    def __init__(self) -> None:
        self.identified = asyncio.Event()
        self.release = asyncio.Event()


@pytest.fixture
def held_scan(lan, monkeypatch):
    ctx, hosts = lan
    hosts[NEW_HOST] = AxeOSSim("gamma", seed=1, mac=MAC).app()

    async def only_new_host_is_open(host: str, port: int, timeout: float = 1.0) -> bool:
        return (host, port) == (NEW_HOST, 80)

    real_probe = discovery_mod.probe_host
    gate = HeldScan()

    async def gated_probe(host, port=None, *, client, timeout=4.0, drivers=None):
        # AxeOS only: the cgminer probe would open a real TCP connection instead of using the simulated network
        found = await real_probe(host, port, client=client, timeout=timeout, drivers=["axeos"])
        gate.identified.set()
        await gate.release.wait()
        return found

    monkeypatch.setattr(discovery_mod, "tcp_open", only_new_host_is_open)
    monkeypatch.setattr(discovery_mod, "probe_host", gated_probe)
    return gate


async def lost_miner(ctx):
    """A miner saved at an address nobody answers on, polled until the fleet calls it offline."""
    probe = (await probe_host(NEW_HOST, 80, client=ctx.http, drivers=["axeos"]))[0]
    stale = probe.model_copy(update={"info": probe.info.model_copy(update={"host": OLD_HOST, "port": 80})})
    rt = ctx.fleet.runtimes[(await ctx.fleet.add_from_probe(stale, name="Garage")).device.id]
    for _ in range(3):
        await ctx.fleet._poll_once(rt)
    assert rt.status == DeviceStatus.OFFLINE
    return rt


def start_heal(ctx) -> asyncio.Task[list[str]]:
    return asyncio.create_task(ctx.discovery.heal_moved_devices(min_offline_s=0))


async def moved_events(ctx):
    return await ctx.store.list_events(types=["device_moved"], limit=50)


async def test_healing_closes_the_driver_it_replaces_exactly_once(lan, held_scan):
    ctx, _ = lan
    rt = await lost_miner(ctx)
    driver = ctx.fleet._ensure_driver(rt)
    closed: list[int] = []

    async def counting_close() -> None:
        closed.append(1)

    driver.close = counting_close  # type: ignore[method-assign]
    held_scan.release.set()

    moved = await start_heal(ctx)

    assert moved == [rt.device.id] and rt.device.host == NEW_HOST
    assert closed == [1]


async def test_healing_does_not_resurrect_a_miner_removed_while_it_scans(lan, held_scan):
    ctx, _ = lan
    rt = await lost_miner(ctx)
    device_id = rt.device.id
    task = start_heal(ctx)
    await asyncio.wait_for(held_scan.identified.wait(), 5)

    assert await ctx.fleet.remove(device_id)
    held_scan.release.set()

    assert await asyncio.wait_for(task, 5) == []
    assert device_id not in ctx.fleet.runtimes
    assert await ctx.store.get_device(device_id) is None
    assert await moved_events(ctx) == []


async def test_healing_leaves_an_endpoint_the_user_edited_while_it_scans(lan, held_scan):
    ctx, _ = lan
    rt = await lost_miner(ctx)
    task = start_heal(ctx)
    await asyncio.wait_for(held_scan.identified.wait(), 5)

    await ctx.fleet.update(rt.device.id, {"host": "10.36.0.99"})
    held_scan.release.set()

    assert await asyncio.wait_for(task, 5) == []
    assert (rt.device.host, rt.device.alt_hosts) == ("10.36.0.99", [])
    stored = await ctx.store.get_device(rt.device.id)
    assert stored is not None and (stored.host, stored.alt_hosts) == ("10.36.0.99", [])
    assert await moved_events(ctx) == []


async def test_healing_waits_for_the_device_lock_but_does_not_hold_it_while_scanning(lan, held_scan):
    ctx, _ = lan
    rt = await lost_miner(ctx)
    task = start_heal(ctx)
    await asyncio.wait_for(held_scan.identified.wait(), 5)

    async with asyncio.timeout(5), rt.lock:  # the scan itself never holds the device lock
        held_scan.release.set()
        for _ in range(20):
            await asyncio.sleep(0.01)
        assert not task.done()  # publishing the new endpoint needs the lock, like every other change
        assert rt.device.host == OLD_HOST

    assert await asyncio.wait_for(task, 5) == [rt.device.id]
    assert rt.device.host == NEW_HOST


async def test_a_failed_save_leaves_the_miner_exactly_as_it_was(lan, held_scan, monkeypatch):
    ctx, _ = lan
    rt = await lost_miner(ctx)
    driver = ctx.fleet._ensure_driver(rt)

    async def failing_save(*args: Any, **kwargs: Any) -> None:
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(ctx.store, "save_device", failing_save)
    held_scan.release.set()

    with contextlib.suppress(sqlite3.OperationalError):
        await start_heal(ctx)

    assert (rt.device.host, rt.device.port, rt.device.alt_hosts) == (OLD_HOST, 80, [])
    assert rt.driver is driver and rt.status == DeviceStatus.OFFLINE
    stored = await ctx.store.get_device(rt.device.id)
    assert stored is not None and (stored.host, stored.alt_hosts) == (OLD_HOST, [])
    assert await moved_events(ctx) == []
