"""Issue #19: a failure after a successful hardware read must not end that miner's polling task.

Each test runs the real ``Fleet._loop`` against a simulator and injects a storage failure into the
work that follows the read (status/event persistence). The loop drives itself: ``rt.wake`` stands in
for the elapsed poll interval so no test depends on wall-clock sleeps.
"""

import asyncio
import sqlite3
import time

import pytest

from bsmm.models import DeviceStatus
from bsmm.sim.axeos import AxeOSSim

from .test_fleet import add

STORAGE_ERROR = "database is locked"
WAIT_S = 5.0
TICK_S = 0.01
# Both run inside _on_success, after the miner has answered.
INJECTION_POINTS = ["_detect_events", "_set_status_async"]


async def until(predicate, rt, timeout_s=WAIT_S):
    """Run poll iterations (by waking the loop) until predicate() holds. False on timeout."""
    deadline = time.monotonic() + timeout_s
    while not predicate():
        if time.monotonic() > deadline:
            return False
        rt.wake.set()
        await asyncio.sleep(TICK_S)
    return True


def inject_storage_failure(monkeypatch, fleet, name, times=None):
    """Make ``fleet.<name>`` raise a storage error ``times`` times (forever when None), then delegate."""
    original = getattr(fleet, name)
    state = {"calls": 0}

    async def flaky(*args, **kwargs):
        state["calls"] += 1
        if times is None or state["calls"] <= times:
            raise sqlite3.OperationalError(STORAGE_ERROR)
        return await original(*args, **kwargs)

    monkeypatch.setattr(fleet, name, flaky)
    return state


def start_loop(fleet, rt):
    fleet._running = True
    rt.task = asyncio.create_task(fleet._loop(rt), name=f"poll-{rt.device.id}")
    return rt.task


@pytest.fixture
async def prepared(lan, monkeypatch):
    """(fleet, runtime, polls). The poll task is not started; ``polls`` records the runtime's
    (last_error, status, telemetry time) at the start of every iteration."""
    ctx, hosts = lan
    monkeypatch.setattr("bsmm.engine.fleet.random.uniform", lambda _low, _high: 0.0)
    result = await add(ctx, hosts, "miner.test", AxeOSSim("gamma", seed=1, mac="AA:BB:CC:00:00:01"))
    fleet = ctx.fleet
    rt = fleet.runtimes[result.device.id]
    polls = []
    original_poll_once = fleet._poll_once

    async def recording_poll_once(runtime):
        polls.append((runtime.last_error, runtime.status, runtime.telemetry.ts if runtime.telemetry else None))
        await original_poll_once(runtime)

    monkeypatch.setattr(fleet, "_poll_once", recording_poll_once)
    yield fleet, rt, polls
    if rt.task is not None:
        rt.task.cancel()
        await asyncio.gather(rt.task, return_exceptions=True)


@pytest.mark.parametrize("name", INJECTION_POINTS)
async def test_one_storage_failure_after_a_good_read_does_not_stop_polling(prepared, monkeypatch, name):
    fleet, rt, polls = prepared
    inject_storage_failure(monkeypatch, fleet, name, times=1)
    task = start_loop(fleet, rt)

    resumed = await until(lambda: len(polls) >= 3 or task.done(), rt)
    assert resumed and not task.done(), "the polling task ended after one transient storage failure"

    assert rt.task is task, "polling must continue on the same task, not a duplicate"
    # What the second iteration saw: the failure of the first one, reported as a monitoring problem.
    last_error, status, first_ts = polls[1]
    assert last_error and STORAGE_ERROR in last_error
    assert status != DeviceStatus.OFFLINE
    # Polling resumed: telemetry advanced past the read that preceded the failure, and the error cleared.
    assert rt.telemetry is not None and first_ts is not None and rt.telemetry.ts > first_ts
    assert await until(lambda: rt.last_error is None, rt)
    assert rt.failures == 0 and rt.status != DeviceStatus.OFFLINE


async def test_persistent_storage_failure_stays_visible_and_is_not_hardware_offline(prepared, monkeypatch):
    fleet, rt, polls = prepared
    inject_storage_failure(monkeypatch, fleet, "_detect_events")
    task = start_loop(fleet, rt)

    # Inspect between iterations only: mid-iteration the status is briefly the one the read produced.
    settled = await until(lambda: task.done() or (len(polls) >= 4 and not rt.lock.locked()), rt)
    assert settled and not task.done(), "the polling task ended while storage was failing"

    assert rt.task is task
    assert rt.last_error and STORAGE_ERROR in rt.last_error
    assert rt.status == DeviceStatus.DEGRADED, "a stalled monitor must not look healthy"
    assert rt.failures == 0 and rt.offline_since is None, "a storage error is not the miner going offline"


async def test_removal_stops_a_failing_poll_task_for_good(prepared, monkeypatch):
    fleet, rt, polls = prepared
    inject_storage_failure(monkeypatch, fleet, "_detect_events")
    task = start_loop(fleet, rt)
    assert await until(lambda: len(polls) >= 2 or task.done(), rt)
    assert not task.done(), "the polling task ended while storage was failing"

    assert await fleet.remove(rt.device.id)

    assert task.done() and rt.device.id not in fleet.runtimes
    seen = len(polls)
    assert not await until(lambda: len(polls) > seen, rt, timeout_s=0.2), "polling continued after removal"
