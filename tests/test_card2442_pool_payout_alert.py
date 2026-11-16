"""Card #2442: a safety alert when a miner's pool or payout settings change.

HashHurdr only reads. It remembers, per miner, the pool host, port and payout address of every pool the miner reports
(its baseline). A different set that is seen on several polls in a row raises one critical event and puts a
"settings changed" badge on the miner. The user answers it with Accept, which only updates HashHurdr's own baseline.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import sqlite3
import time
from pathlib import Path

import httpx
import pytest

from bsmm.api.app import create_app
from bsmm.config import RuntimeConfig
from bsmm.context import AppContext
from bsmm.engine.fleet import Fleet
from bsmm.models import Channel, Severity
from bsmm.notify.channels import CHANNEL_CLASSES, BaseChannel, Notification
from bsmm.sim.axeos import EXAMPLE_ADDR, AxeOSSim
from bsmm.storage.db import MIGRATIONS

from .conftest import MultiHostTransport
from .test_fleet import events, poll
from .test_foundation_fleet import miner

EVENT_TYPE = "pool_settings_changed"
RULE_ID = "rule_pool_settings_changed"
ACCEPT = "/api/v1/events/{}/accept-pool-change"
THRESHOLD = 3  # polling.offline_after_failures: the same number of polls in a row confirms a change
HOST = "miner.test"

ADDR_A = EXAMPLE_ADDR
ADDR_B = "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"  # a second valid mainnet address (BIP 173 test vector)
PASSWORD = "pw-hunter2-never-show"

#: What the simulated miner reports before any change (see AxeOSSim).
PRIMARY = {"slot": "primary", "host": "192.168.1.10", "port": 2018, "payout": ADDR_A}
FALLBACK = {"slot": "fallback", "host": "solo.ckpool.org", "port": 3333, "payout": ADDR_A}
BASELINE = [PRIMARY, FALLBACK]
CHANGED_PRIMARY = {"slot": "primary", "host": "other-pool.example.net", "port": 4444, "payout": ADDR_B}
CHANGED = {"stratumURL": "other-pool.example.net", "stratumPort": 4444, "stratumUser": f"{ADDR_B}.sim1"}
ORIGINAL = {"stratumURL": "192.168.1.10", "stratumPort": 2018, "stratumUser": f"{ADDR_A}.sim1"}


# --- helpers -----------------------------------------------------------------------------------------------------------


async def pool_events(ctx):
    return await ctx.store.list_events(types=[EVENT_TYPE], limit=100)


async def watched(ctx, hosts):
    """A miner whose first reading has set its baseline."""
    did, sim = await miner(ctx, hosts)
    await poll(ctx, did)
    return did, sim


async def polls(ctx, did, count=THRESHOLD):
    for _ in range(count):
        await poll(ctx, did)


async def raised(ctx, hosts, change=CHANGED):
    """A miner whose settings changed and stayed changed long enough to be confirmed."""
    did, sim = await watched(ctx, hosts)
    sim.settings.update(change)
    await polls(ctx, did)
    [ev] = await pool_events(ctx)
    return did, sim, ev


def changes_of(ev):
    return [(c["slot"], c["setting"], c["old"], c["new"]) for c in ev.data["changes"]]


@pytest.fixture
async def outbox(lan, monkeypatch):
    """Notifications delivered to one capturing channel, with the built-in rules in place."""
    ctx, _ = lan
    sent: list[Notification] = []

    class Capture(BaseChannel):
        kind = "capture"
        label = "Capture"

        async def send(self, n: Notification) -> None:
            sent.append(n)

    monkeypatch.setitem(CHANNEL_CLASSES, "capture", Capture)
    await ctx.store.save_channel(Channel(id="ch_main", kind="capture", name="Main", config={}))
    await ctx.alerts.ensure_default_rules()
    return sent


# --- baseline ----------------------------------------------------------------------------------------------------------


async def test_the_default_confirmation_is_three_polls_in_a_row(lan):
    ctx, _ = lan
    assert ctx.settings.current.polling.offline_after_failures == THRESHOLD


async def test_the_first_reading_sets_the_baseline_without_an_alert(lan):
    ctx, hosts = lan
    did, _ = await miner(ctx, hosts)
    await poll(ctx, did)
    row = await ctx.store.get_pool_watch(did)
    assert row is not None
    assert row.baseline == BASELINE and row.observed is None and row.event_id is None
    assert await pool_events(ctx) == []
    assert ctx.fleet.view(did).pool_change is None


async def test_unchanged_settings_never_alert(lan):
    ctx, hosts = lan
    did, sim = await watched(ctx, hosts)
    sim.settings["stratumUser"] = f"{ADDR_A}.another-worker"  # a worker name is not a pool or payout setting
    await polls(ctx, did, THRESHOLD + 3)
    assert await pool_events(ctx) == []
    assert (await ctx.store.get_pool_watch(did)).baseline == BASELINE


async def test_upgrading_a_1_4_database_keeps_everything_and_raises_no_alert(tmp_path: Path):
    path = tmp_path / "bsmm.db"
    with contextlib.closing(sqlite3.connect(path)) as old:  # a database exactly as 1.4.x left it: schema 2, no pool_watch
        old.executescript(MIGRATIONS[0][1])
        old.executescript(MIGRATIONS[1][1])
        old.execute("PRAGMA user_version = 2")
        old.execute(
            "INSERT INTO devices (id, name, driver, family, model, host, port, mac, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            ("dev_old", "Old Garage", "axeos", "bitaxe", "Gamma", "old.test", 80, "AA:BB:CC:00:00:77", 1.0))
        old.execute("INSERT INTO events (ts, type, severity, title) VALUES (1.0, 'device_added', 'info', 'Added Old Garage')")
        old.execute("INSERT INTO kv (key, value) VALUES ('keep.me', '\"precious\"')")
        old.commit()
    hosts = {"old.test": AxeOSSim("gamma", seed=1, mac="AA:BB:CC:00:00:77").app()}
    http = httpx.AsyncClient(transport=MultiHostTransport(hosts), headers={"Connection": "close"}, timeout=5.0)
    ctx = await AppContext.create(RuntimeConfig(data_dir=tmp_path, offline=True), http=http)
    try:
        assert await ctx.store.db.scalar("SELECT COUNT(*) FROM pool_watch") == 0  # the new table exists and starts empty
        assert await ctx.store.db.schema_version() == MIGRATIONS[-1][0]
        assert [d.name for d in await ctx.store.list_devices()] == ["Old Garage"]
        assert await events(ctx) == ["device_added"]
        assert await ctx.store.kv_get("keep.me") == "precious"
        await ctx.alerts.ensure_default_rules()
        assert (await ctx.store.get_rule(RULE_ID)).enabled  # the new built-in rule arrives on the next start

        [dev] = await ctx.store.list_devices()
        rt = ctx.fleet._spawn(dev)
        await ctx.fleet._poll_once(rt)  # the first reading after the upgrade: baseline, no alert
        assert (await ctx.store.get_pool_watch(dev.id)).baseline == BASELINE
        await polls(ctx, dev.id, THRESHOLD)
        assert await pool_events(ctx) == []
    finally:
        await ctx.fleet.stop()
        await ctx.http.aclose()
        await ctx.store.close()


async def test_removing_a_miner_removes_its_baseline(lan):
    ctx, hosts = lan
    did, _ = await watched(ctx, hosts)
    assert await ctx.fleet.remove(did)
    assert await ctx.store.get_pool_watch(did) is None
    assert await ctx.store.db.scalar("SELECT COUNT(*) FROM pool_watch") == 0


# --- what is a change --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("patch", "expected"),
    [
        ({"stratumURL": "other-pool.example.net"}, [("primary", "pool_address", "192.168.1.10", "other-pool.example.net")]),
        ({"stratumPort": 4444}, [("primary", "pool_port", "2018", "4444")]),
        ({"stratumUser": f"{ADDR_B}.sim1"}, [("primary", "payout_address", ADDR_A, ADDR_B)]),
        ({"fallbackStratumURL": "other.example.net"}, [("fallback", "pool_address", "solo.ckpool.org", "other.example.net")]),
        ({"fallbackStratumPort": 4444}, [("fallback", "pool_port", "3333", "4444")]),
        ({"fallbackStratumUser": f"{ADDR_B}.x"}, [("fallback", "payout_address", ADDR_A, ADDR_B)]),
        ({"stratumURL": "  OTHER-POOL.Example.NET "}, [("primary", "pool_address", "192.168.1.10", "other-pool.example.net")]),
        ({"stratumUser": f"{ADDR_B.upper()}.sim1"}, [("primary", "payout_address", ADDR_A, ADDR_B)]),
    ],
)
async def test_a_changed_primary_or_fallback_pool_or_payout_address_is_reported(lan, patch, expected):
    ctx, hosts = lan
    did, sim = await watched(ctx, hosts)
    sim.settings.update(patch)
    await polls(ctx, did)
    [ev] = await pool_events(ctx)
    assert changes_of(ev) == expected


async def test_a_fallback_pool_disappearing_is_reported(lan):
    ctx, hosts = lan
    did, sim = await watched(ctx, hosts)
    sim.settings["fallbackStratumURL"] = ""
    await polls(ctx, did)
    [ev] = await pool_events(ctx)
    assert changes_of(ev) == [("fallback", "pool_address", "solo.ckpool.org", None), ("fallback", "pool_port", "3333", None),
                              ("fallback", "payout_address", ADDR_A, None)]


async def test_a_fallback_pool_appearing_is_reported(lan):
    ctx, hosts = lan
    did, sim = await miner(ctx, hosts)
    sim.settings["fallbackStratumURL"] = ""
    await poll(ctx, did)
    assert (await ctx.store.get_pool_watch(did)).baseline == [PRIMARY]
    sim.settings["fallbackStratumURL"] = "solo.ckpool.org"
    await polls(ctx, did)
    [ev] = await pool_events(ctx)
    assert changes_of(ev) == [("fallback", "pool_address", None, "solo.ckpool.org"), ("fallback", "pool_port", None, "3333"),
                              ("fallback", "payout_address", None, ADDR_A)]


@pytest.mark.parametrize("user", [f"{ADDR_A}.rig2", ADDR_A, f"{ADDR_A.upper()}.RIG1"])
async def test_a_worker_name_only_change_is_ignored(lan, user):
    ctx, hosts = lan
    did, sim = await watched(ctx, hosts)
    sim.settings["stratumUser"] = user
    await polls(ctx, did, THRESHOLD + 2)
    assert await pool_events(ctx) == []


# --- stability: one odd read, an empty list or a restarting miner is not a change --------------------------------------


@pytest.mark.parametrize("odd_polls", range(1, THRESHOLD))
async def test_a_short_lived_change_is_not_a_change(lan, odd_polls):
    ctx, hosts = lan
    did, sim = await watched(ctx, hosts)
    sim.settings["stratumURL"] = "odd.example.net"
    await polls(ctx, did, odd_polls)
    sim.settings.update(ORIGINAL)
    await polls(ctx, did, THRESHOLD)
    assert await pool_events(ctx) == []
    assert ctx.fleet.view(did).pool_change is None


async def test_odd_readings_that_are_not_consecutive_never_add_up(lan):
    ctx, hosts = lan
    did, sim = await watched(ctx, hosts)
    for _ in range(THRESHOLD * 2):
        sim.settings["stratumURL"] = "odd.example.net"
        await poll(ctx, did)
        sim.settings.update(ORIGINAL)
        await poll(ctx, did)
    assert await pool_events(ctx) == []


async def test_an_empty_pool_list_is_not_a_change_and_keeps_the_baseline(lan):
    ctx, hosts = lan
    did, sim = await watched(ctx, hosts)
    sim.settings.update(stratumURL="", fallbackStratumURL="")  # the miner reports no pools at all
    await polls(ctx, did, THRESHOLD + 2)
    assert await pool_events(ctx) == []
    assert (await ctx.store.get_pool_watch(did)).baseline == BASELINE
    sim.settings.update(ORIGINAL, fallbackStratumURL="solo.ckpool.org")
    await polls(ctx, did, THRESHOLD)
    assert await pool_events(ctx) == []


async def test_an_empty_reading_between_changed_readings_restarts_the_count(lan):
    ctx, hosts = lan
    did, sim = await watched(ctx, hosts)
    sim.settings.update(CHANGED)
    await polls(ctx, did, THRESHOLD - 1)
    sim.settings.update(stratumURL="", fallbackStratumURL="")
    await poll(ctx, did)
    sim.settings.update(CHANGED, fallbackStratumURL="solo.ckpool.org")
    await poll(ctx, did)
    assert await pool_events(ctx) == []  # only one changed reading since the gap
    await polls(ctx, did, THRESHOLD - 1)
    assert len(await pool_events(ctx)) == 1  # the change is real: it held for the full count


async def test_an_offline_miner_is_not_a_change(lan):
    ctx, hosts = lan
    did, _ = await watched(ctx, hosts)
    sim_app = hosts.pop(HOST)
    await polls(ctx, did, THRESHOLD + 2)  # unplugged, then offline
    hosts[HOST] = sim_app
    await polls(ctx, did, THRESHOLD)  # back, with the same settings
    assert await pool_events(ctx) == []
    assert (await ctx.store.get_pool_watch(did)).baseline == BASELINE


async def test_a_missed_poll_restarts_the_count(lan):
    ctx, hosts = lan
    did, sim = await watched(ctx, hosts)
    sim.settings.update(CHANGED)
    await polls(ctx, did, THRESHOLD - 1)
    sim_app = hosts.pop(HOST)
    await poll(ctx, did)  # the miner did not answer (restarting)
    hosts[HOST] = sim_app
    await poll(ctx, did)
    assert await pool_events(ctx) == []
    await polls(ctx, did, THRESHOLD - 1)
    assert len(await pool_events(ctx)) == 1


# --- the event ---------------------------------------------------------------------------------------------------------


async def test_a_confirmed_change_raises_one_critical_event_with_full_old_and_new_values(lan):
    ctx, hosts = lan
    did, sim = await watched(ctx, hosts)
    sim.settings.update(CHANGED)
    for _ in range(THRESHOLD - 1):
        await poll(ctx, did)
        assert await pool_events(ctx) == []  # not yet: still waiting for confirmation
    await poll(ctx, did)
    [ev] = await pool_events(ctx)
    assert ev.severity == Severity.CRITICAL and ev.device_id == did and ev.ack_ts is None
    assert changes_of(ev) == [("primary", "pool_address", "192.168.1.10", "other-pool.example.net"),
                              ("primary", "pool_port", "2018", "4444"), ("primary", "payout_address", ADDR_A, ADDR_B)]
    pending = ctx.fleet.view(did).pool_change
    assert pending is not None and pending.event_id == ev.id
    assert [(c.slot, c.setting, c.old, c.new) for c in pending.changes] == changes_of(ev)
    row = await ctx.store.get_pool_watch(did)
    assert row.baseline == BASELINE, "the baseline moves only when the user accepts"
    assert row.observed == [CHANGED_PRIMARY, FALLBACK] and row.event_id == ev.id


async def test_a_change_that_stays_raises_exactly_one_event(lan):
    ctx, hosts = lan
    did, _, ev = await raised(ctx, hosts)
    await polls(ctx, did, THRESHOLD * 3)
    assert [e.id for e in await pool_events(ctx)] == [ev.id]


async def test_a_second_different_change_raises_a_new_event_and_resolves_the_older_one(lan):
    ctx, hosts = lan
    did, sim, first = await raised(ctx, hosts)
    sim.settings["stratumURL"] = "third.example.net"
    await polls(ctx, did)
    second, older = await pool_events(ctx)
    assert older.id == first.id and older.ack_ts is not None
    assert second.ack_ts is None and ctx.fleet.view(did).pool_change.event_id == second.id


async def test_a_change_stays_open_when_the_miner_reports_the_recorded_settings_again(lan):
    ctx, hosts = lan
    did, sim, ev = await raised(ctx, hosts)
    sim.settings.update(ORIGINAL)
    await polls(ctx, did, THRESHOLD * 3)  # well past the confirmation count
    [only] = await pool_events(ctx)  # no second event
    assert only.id == ev.id and only.ack_ts is None, "only the user answers a change"
    pending = ctx.fleet.view(did).pool_change
    assert pending is not None and pending.event_id == ev.id and pending.changes
    assert [(c.slot, c.setting, c.old, c.new) for c in pending.changes] == changes_of(ev)  # still shows what was seen
    row = await ctx.store.get_pool_watch(did)
    assert row.baseline == BASELINE and row.event_id == ev.id


async def test_a_steady_return_writes_nothing_on_ordinary_polls(lan, monkeypatch):
    ctx, hosts = lan
    did, sim, _ = await raised(ctx, hosts)
    sim.settings.update(ORIGINAL)
    await polls(ctx, did)  # the return is confirmed once
    writes = []
    save = ctx.store.save_pool_watch

    async def counting(row):
        writes.append(row)
        await save(row)

    monkeypatch.setattr(ctx.store, "save_pool_watch", counting)
    await polls(ctx, did, THRESHOLD * 4)
    assert writes == [], "a miner steadily reporting the recorded settings must not cost a write per poll"
    assert ctx.fleet.view(did).pool_change is not None


@pytest.mark.parametrize("via_route", [True, False], ids=["route", "fleet"])
async def test_answering_a_change_the_miner_went_back_from_keeps_the_recorded_settings(api, via_route):
    c, ctx, hosts = api
    did, sim, ev = await raised(ctx, hosts)
    sim.settings.update(ORIGINAL)
    await polls(ctx, did, THRESHOLD * 2)
    calls_before = list(sim.calls)
    if via_route:
        response = await c.post(ACCEPT.format(ev.id))
        assert response.status_code == 200, response.text
    else:
        assert (await ctx.fleet.accept_pool_change(did, ev.id)).pool_change is None
    assert sim.calls == calls_before, "accepting must not send a single request to the miner"
    row = await ctx.store.get_pool_watch(did)
    assert row.baseline == BASELINE, "the abandoned settings never become the record"
    assert row.observed is None and row.event_id is None and row.changed_ts is None
    [stored] = await pool_events(ctx)
    assert stored.id == ev.id and stored.ack_ts is not None
    assert ctx.fleet.view(did).pool_change is None
    await polls(ctx, did, THRESHOLD * 2)
    assert [e.id for e in await pool_events(ctx)] == [ev.id]
    assert ctx.fleet.view(did).pool_change is None
    assert (await ctx.store.get_pool_watch(did)).baseline == BASELINE


async def test_a_change_the_miner_went_back_from_is_still_open_after_a_restart(lan):
    ctx, hosts = lan
    did, sim, ev = await raised(ctx, hosts)
    sim.settings.update(ORIGINAL)
    await polls(ctx, did, THRESHOLD)
    fleet = Fleet(ctx.store, ctx.settings, ctx.bus, ctx.events, ctx.http)  # what a restart builds from the saved data
    [dev] = await ctx.store.list_devices()
    rt = fleet._spawn(dev)
    await fleet._load_pool_changes()
    try:
        pending = fleet.view(did).pool_change
        assert pending is not None and pending.event_id == ev.id and pending.changes
        assert [(c.slot, c.setting, c.old, c.new) for c in pending.changes] == changes_of(ev)
        for _ in range(THRESHOLD * 2):
            await fleet._poll_once(rt)
        assert fleet.view(did).pool_change is not None
    finally:
        await fleet.stop()
    [only] = await pool_events(ctx)
    assert only.id == ev.id and only.ack_ts is None


async def test_a_different_change_after_a_return_raises_its_own_event(lan):
    ctx, hosts = lan
    did, sim, first = await raised(ctx, hosts)
    sim.settings.update(ORIGINAL)
    await polls(ctx, did, THRESHOLD * 2)
    assert (await pool_events(ctx))[0].ack_ts is None  # still waiting for an answer
    sim.settings["stratumURL"] = "third.example.net"
    await polls(ctx, did)
    second, older = await pool_events(ctx)
    assert older.id == first.id and older.ack_ts is not None  # replaced by the newer change
    assert second.ack_ts is None and changes_of(second) == [("primary", "pool_address", "192.168.1.10", "third.example.net")]
    assert ctx.fleet.view(did).pool_change.event_id == second.id
    assert (await ctx.store.get_pool_watch(did)).baseline == BASELINE


async def test_a_restart_does_not_repeat_the_alert(lan):
    ctx, hosts = lan
    did, _, ev = await raised(ctx, hosts)
    fleet = Fleet(ctx.store, ctx.settings, ctx.bus, ctx.events, ctx.http)  # what a restart builds from the saved data
    [dev] = await ctx.store.list_devices()
    rt = fleet._spawn(dev)
    await fleet._load_pool_changes()
    try:
        assert fleet.view(did).pool_change.event_id == ev.id  # the badge survives the restart
        for _ in range(THRESHOLD * 2):
            await fleet._poll_once(rt)
    finally:
        await fleet.stop()
    assert [e.id for e in await pool_events(ctx)] == [ev.id]


async def test_a_restart_with_unchanged_settings_stays_quiet(lan):
    ctx, hosts = lan
    did, _ = await watched(ctx, hosts)
    fleet = Fleet(ctx.store, ctx.settings, ctx.bus, ctx.events, ctx.http)
    [dev] = await ctx.store.list_devices()
    rt = fleet._spawn(dev)
    await fleet._load_pool_changes()
    try:
        for _ in range(THRESHOLD * 2):
            await fleet._poll_once(rt)
    finally:
        await fleet.stop()
    assert await pool_events(ctx) == [] and fleet.view(did).pool_change is None


async def test_a_change_made_while_stopped_is_reported_once_after_the_restart(lan):
    ctx, hosts = lan
    did, sim = await watched(ctx, hosts)
    sim.settings.update(CHANGED)  # changed while HashHurdr was not running
    fleet = Fleet(ctx.store, ctx.settings, ctx.bus, ctx.events, ctx.http)
    [dev] = await ctx.store.list_devices()
    rt = fleet._spawn(dev)
    await fleet._load_pool_changes()
    try:
        for _ in range(THRESHOLD * 3):
            await fleet._poll_once(rt)
    finally:
        await fleet.stop()
    assert len(await pool_events(ctx)) == 1


GATED_WINDOW_S = 2.0  # how long the startup rebuild is held while the miner's poll tasks are woken
CONFIRM_WITHIN_S = 5.0  # generous bound for the polls that confirm a change; they take milliseconds
WAKE_TICK_S = 0.005
THIRD = {**CHANGED_PRIMARY, "host": "third.example.net"}  # what the miner reports in the startup test below


async def wake_until(fleet, predicate, seconds: float) -> bool:
    """Wake the real poll tasks of ``fleet`` over and over until ``predicate`` holds or the time is up."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + seconds
    while not await predicate() and loop.time() < deadline:
        for rt in fleet.runtimes.values():
            rt.wake.set()
        await asyncio.sleep(WAKE_TICK_S)
    return await predicate()


@pytest.mark.parametrize("via_route", [True, False], ids=["route", "fleet"])
async def test_a_startup_rebuild_never_replaces_a_newer_pool_change(api, monkeypatch, via_route):
    """The rebuild after a restart reads the waiting change and its event. A poll must not be able to confirm a newer
    change in between and then have the older one put back, which would leave the notice showing a change that can no
    longer be answered."""
    c, ctx, hosts = api
    did, sim, first = await raised(ctx, hosts)  # a change that waits for an answer, as at a restart
    sim.settings["stratumURL"] = "third.example.net"  # a different change, which the polls confirm after the restart
    monkeypatch.setattr("bsmm.engine.fleet.random.uniform", lambda low, high: 0.0)  # the first poll starts at once
    rebuilding, release = asyncio.Event(), asyncio.Event()
    get_event = ctx.store.get_event

    async def held(event_id):  # the rebuild is slow to read the event of the waiting change
        rebuilding.set()
        await release.wait()
        return await get_event(event_id)

    monkeypatch.setattr(ctx.store, "get_event", held)
    fleet = Fleet(ctx.store, ctx.settings, ctx.bus, ctx.events, ctx.http)  # what a restart builds from the saved data
    starting = asyncio.create_task(fleet.start())
    try:
        await asyncio.wait_for(rebuilding.wait(), CONFIRM_WITHIN_S)

        async def newer_event_exists():
            return len(await pool_events(ctx)) == 2

        await wake_until(fleet, newer_event_exists, GATED_WINDOW_S)  # polls that run while the rebuild waits
        release.set()
        await asyncio.wait_for(starting, CONFIRM_WITHIN_S)

        async def notice_shows_newest_event():
            found = await pool_events(ctx)
            pending = fleet.view(did).pool_change
            return len(found) == 2 and pending is not None and pending.event_id == found[0].id

        assert await wake_until(fleet, notice_shows_newest_event, CONFIRM_WITHIN_S), (
            "the notice must show the newer change, not the one it replaced")
        second, older = await pool_events(ctx)
        assert older.id == first.id and older.ack_ts is not None and second.ack_ts is None
        tasks = [rt.task for rt in fleet.runtimes.values() if rt.task]
        for task in tasks:  # nothing polls from here on, so the miner's request log only changes if Accept sends something
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        calls_before = list(sim.calls)
        if via_route:
            monkeypatch.setattr(ctx, "fleet", fleet)
            response = await c.post(ACCEPT.format(second.id))
            assert response.status_code == 200, response.text
        else:
            assert (await fleet.accept_pool_change(did, second.id)).pool_change is None
        assert sim.calls == calls_before, "accepting must not send a single request to the miner"
        row = await ctx.store.get_pool_watch(did)
        assert row.baseline == [THIRD, FALLBACK] and row.observed is None and row.event_id is None
        assert fleet.view(did).pool_change is None
        assert (await ctx.store.get_event(second.id)).ack_ts is not None
    finally:
        release.set()
        await asyncio.gather(starting, return_exceptions=True)
        await fleet.stop()


# --- Accept: only HashHurdr's own record changes -------------------------------------------------------------------------


async def test_accept_updates_the_baseline_and_resolves_the_event_without_touching_the_miner(api):
    c, ctx, hosts = api
    did, sim, ev = await raised(ctx, hosts)
    calls_before = list(sim.calls)
    response = await c.post(ACCEPT.format(ev.id))
    assert response.status_code == 200, response.text
    assert response.json()["ok"] is True
    assert sim.calls == calls_before, "accepting must not send a single request to the miner"
    row = await ctx.store.get_pool_watch(did)
    assert row.baseline == [CHANGED_PRIMARY, FALLBACK] and row.observed is None and row.event_id is None
    [stored] = await pool_events(ctx)
    assert stored.id == ev.id and stored.ack_ts is not None
    assert ctx.fleet.view(did).pool_change is None
    await polls(ctx, did, THRESHOLD * 2)  # the accepted settings are the new normal
    assert len(await pool_events(ctx)) == 1


async def test_after_accept_the_next_change_alerts_again(api):
    c, ctx, hosts = api
    did, sim, ev = await raised(ctx, hosts)
    assert (await c.post(ACCEPT.format(ev.id))).status_code == 200
    sim.settings["stratumURL"] = "next.example.net"
    await polls(ctx, did)
    assert len(await pool_events(ctx)) == 2


async def test_accepting_twice_or_a_superseded_event_is_refused(api):
    c, ctx, hosts = api
    did, sim, first = await raised(ctx, hosts)
    sim.settings["stratumURL"] = "third.example.net"
    await polls(ctx, did)
    older = await c.post(ACCEPT.format(first.id))  # resolved when the newer change came in
    assert older.status_code == 409 and older.json()["error"]["code"] == "pool_change_not_pending"
    second = (await pool_events(ctx))[0]
    assert (await c.post(ACCEPT.format(second.id))).status_code == 200
    again = await c.post(ACCEPT.format(second.id))
    assert again.status_code == 409 and again.json()["error"]["code"] == "pool_change_not_pending"


async def test_accept_needs_an_event_of_this_kind(api):
    c, ctx, hosts = api
    await watched(ctx, hosts)
    assert (await c.post(ACCEPT.format(999_999))).status_code == 404
    [added] = await ctx.store.list_events(types=["device_added"])
    assert (await c.post(ACCEPT.format(added.id))).status_code == 404


async def test_the_not_found_hint_points_at_the_miners_pool_change(api):
    # "Mark all as seen" can leave the unacked list empty while a change still waits (#2455).
    c, ctx, hosts = api
    await watched(ctx, hosts)
    for event_id in (999_999, (await ctx.store.list_events(types=["device_added"]))[0].id):
        r = await c.post(ACCEPT.format(event_id))
        assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
        hint = r.json()["error"]["hint"]
        assert "pool_change" in hint
        assert "unacked=true" not in hint


@pytest.mark.parametrize("went_back", [False, True], ids=["still_changed", "went_back"])
async def test_a_waiting_change_stays_answerable_after_event_retention(api, went_back):
    c, ctx, hosts = api
    did, sim, ev = await raised(ctx, hosts)
    if went_back:
        sim.settings.update(ORIGINAL)
        await polls(ctx, did, THRESHOLD * 2)
    [added] = await ctx.store.list_events(types=["device_added"])
    long_ago = time.time() - 400 * 86400  # far older than any allowed retention (event_days is at least 7)
    await ctx.store.db.execute("UPDATE events SET ts = ? WHERE id IN (?, ?)", (long_ago, ev.id, added.id))

    await ctx.store.prune_events(keep_days=7)  # the call housekeeping makes with retention.event_days

    assert await ctx.store.get_event(added.id) is None, "ordinary old events are still pruned"
    assert await ctx.store.get_event(ev.id) is not None, "the event of a waiting change is kept"
    assert ctx.fleet.view(did).pool_change.event_id == ev.id
    calls_before = list(sim.calls)
    response = await c.post(ACCEPT.format(ev.id))
    assert response.status_code == 200, response.text
    assert sim.calls == calls_before, "accepting must not send a single request to the miner"
    row = await ctx.store.get_pool_watch(did)
    assert row.baseline == (BASELINE if went_back else [CHANGED_PRIMARY, FALLBACK])
    assert row.observed is None and row.event_id is None
    assert ctx.fleet.view(did).pool_change is None
    await ctx.store.prune_events(keep_days=7)  # once answered, the old event follows the normal retention
    assert await ctx.store.get_event(ev.id) is None


async def test_accept_is_a_control_scope_action(api):
    c, ctx, hosts = api
    did, _, ev = await raised(ctx, hosts)
    assert (await c.post("/api/v1/auth/password", json={"new_password": "correct horse battery"})).status_code == 200
    clients = {}
    for scope in ("read", "control"):
        token = (await c.post("/api/v1/auth/tokens", json={"name": scope, "scope": scope})).json()["token"]
        clients[scope] = httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(ctx=ctx)), base_url="http://bsmm.test",
                                           headers={"Authorization": f"Bearer {token}"})
    try:
        denied = await clients["read"].post(ACCEPT.format(ev.id))
        assert denied.status_code == 403 and denied.json()["error"]["code"] == "insufficient_scope"
        assert ctx.fleet.view(did).pool_change is not None
        assert (await clients["read"].get(f"/api/v1/devices/{did}")).json()["pool_change"]["event_id"] == ev.id  # reading is allowed
        assert (await clients["control"].post(ACCEPT.format(ev.id))).status_code == 200
        assert ctx.fleet.view(did).pool_change is None
    finally:
        for client in clients.values():
            await client.aclose()


async def test_the_accept_route_is_documented_and_no_miner_control_route_appears(api):
    c, *_ = api
    spec = (await c.get("/openapi.json")).json()
    operation = spec["paths"]["/api/v1/events/{event_id}/accept-pool-change"]["post"]
    assert operation["operationId"] == "acceptPoolSettingsChange"
    assert [path for path in spec["paths"] if "/devices/" in path and "pool" in path] == []


# --- what the user sees ---------------------------------------------------------------------------------------------------


async def test_the_dashboard_api_keeps_full_values_while_the_notification_shortens_addresses(api, outbox):
    c, ctx, hosts = api
    did, _, ev = await raised(ctx, hosts)
    await ctx.alerts.handle_event(ev.model_dump(mode="json"))
    [n] = outbox
    assert n.type == EVENT_TYPE and n.severity == Severity.CRITICAL and n.device_id == did
    text = json.dumps(n.to_json())
    for address in (ADDR_A, ADDR_B):
        assert address not in text, "a notification must not carry a full payout address"
        assert address[:8] in text and address[-6:] in text
    assert "other-pool.example.net" in text and "4444" in text

    listed = (await c.get("/api/v1/events", params={"type": EVENT_TYPE})).json()["events"]
    assert [e["id"] for e in listed] == [ev.id]
    assert changes_of(ev) == [(x["slot"], x["setting"], x["old"], x["new"]) for x in listed[0]["data"]["changes"]]
    assert ADDR_A in json.dumps(listed) and ADDR_B in json.dumps(listed)
    view = (await c.get(f"/api/v1/devices/{did}")).json()
    assert view["pool_change"]["event_id"] == ev.id
    assert {(x["old"], x["new"]) for x in view["pool_change"]["changes"]} >= {(ADDR_A, ADDR_B)}


async def test_the_event_is_listed_as_unresolved_until_accepted(api):
    c, ctx, hosts = api
    _, _, ev = await raised(ctx, hosts)
    unresolved = (await c.get("/api/v1/events", params={"type": EVENT_TYPE, "unacked": "true"})).json()["events"]
    assert [e["id"] for e in unresolved] == [ev.id]
    await c.post(ACCEPT.format(ev.id))
    assert (await c.get("/api/v1/events", params={"type": EVENT_TYPE, "unacked": "true"})).json()["events"] == []


async def test_pool_passwords_never_appear_anywhere(api, outbox):
    c, ctx, hosts = api
    did, sim = await miner(ctx, hosts)
    original_info = sim.info
    sim.info = lambda: {**original_info(), "stratumPassword": PASSWORD, "fallbackStratumPassword": PASSWORD}
    await poll(ctx, did)
    sim.settings.update(CHANGED)
    await polls(ctx, did)
    [ev] = await pool_events(ctx)
    await ctx.alerts.handle_event(ev.model_dump(mode="json"))
    assert outbox

    seen = [json.dumps(n.to_json()) for n in outbox]
    seen.append(json.dumps([dict(r) for r in await ctx.store.db.fetchall("SELECT * FROM pool_watch")]))
    seen.append(json.dumps([dict(r) for r in await ctx.store.db.fetchall("SELECT * FROM events")]))
    seen.append(ctx.fleet.view(did).model_dump_json())
    for path in (f"/api/v1/devices/{did}", "/api/v1/events", "/api/v1/overview", f"/api/v1/devices/{did}/raw"):
        seen.append((await c.get(path)).text)
    assert PASSWORD not in "\n".join(seen)


# --- the built-in rule ---------------------------------------------------------------------------------------------------


async def test_the_built_in_rule_is_on_by_default_critical_and_editable(api, outbox):
    c, ctx, hosts = api
    rule = await ctx.store.get_rule(RULE_ID)
    assert rule is not None and rule.builtin and rule.kind == EVENT_TYPE
    assert rule.enabled is True and rule.severity == Severity.CRITICAL and rule.cooldown_s == 0

    spec = next(t for t in (await c.get("/api/v1/alerts/rule-types")).json()["rule_types"] if t["kind"] == EVENT_TYPE)
    assert spec["mode"] == "event" and spec["severity"] == "critical" and spec["enabled_by_default"] is True

    patched = await c.patch(f"/api/v1/alerts/rules/{RULE_ID}", json={"severity": "warning", "channel_ids": ["ch_main"]})
    assert patched.status_code == 200 and patched.json()["rule"]["severity"] == "warning"
    assert (await c.patch(f"/api/v1/alerts/rules/{RULE_ID}", json={"severity": "critical"})).status_code == 200
    assert (await c.delete(f"/api/v1/alerts/rules/{RULE_ID}")).status_code == 400  # built-in rules can only be switched off


async def test_switching_the_rule_off_stops_the_notification_but_not_the_detection(api, outbox):
    c, ctx, hosts = api
    assert (await c.patch(f"/api/v1/alerts/rules/{RULE_ID}", json={"enabled": False})).status_code == 200
    did, _, ev = await raised(ctx, hosts)
    await ctx.alerts.handle_event(ev.model_dump(mode="json"))
    assert outbox == []
    assert ctx.fleet.view(did).pool_change is not None  # the badge and the event remain


async def test_the_rule_is_recreated_for_a_database_that_lacks_it(lan, outbox):
    ctx, _ = lan
    await ctx.store.delete_rule(RULE_ID)
    await ctx.alerts.ensure_default_rules()
    rule = await ctx.store.get_rule(RULE_ID)
    assert rule is not None and rule.enabled and rule.severity == Severity.CRITICAL


async def test_the_rule_notifies_through_the_users_channels(lan, outbox):
    ctx, hosts = lan
    _, _, ev = await raised(ctx, hosts)
    await ctx.alerts.handle_event(ev.model_dump(mode="json"))
    assert len(outbox) == 1
    await ctx.alerts.handle_event(ev.model_dump(mode="json"))  # the same event is never sent twice
    assert len(outbox) == 1
