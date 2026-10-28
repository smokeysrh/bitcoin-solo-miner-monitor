"""The alert engine: rule life-cycle (pending -> firing -> reminder -> resolved), every built-in rule,
scoping, persistence across restarts, event rules and rule management.

Miners are the real simulators polled through the real drivers; the engine is driven tick by tick with a
controllable clock (``AlertEngine.tick(now)`` takes the time as an argument) and notifications land in a
capturing channel registered in ``CHANNEL_CLASSES``. Nothing sleeps.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import time
from types import SimpleNamespace
from typing import Any

import pytest

import bsmm.engine.alerts as alerts_mod
from bsmm.engine.alerts import (
    EVALUATORS,
    RESOLVE_AFTER_S,
    RULE_SPECS,
    AlertEngine,
    EvalContext,
    in_scope,
    validate_rule,
)
from bsmm.engine.network import NetworkState, SourceHealth
from bsmm.models import AlertRule, Channel, DeviceStatus, DeviceView, FleetSummary, Severity, Telemetry
from bsmm.notify.channels import CHANNEL_CLASSES, BaseChannel, Notification
from bsmm.settings import Settings
from bsmm.sim.axeos import AxeOSSim
from bsmm.storage.samples import telemetry_to_row

# --- harness ------------------------------------------------------------------------------------------------------


class Clock:
    """The engine's notion of 'now'. Starts at the real time so ages in messages look sensible."""

    def __init__(self) -> None:
        self.t = time.time()


def install_overrides(sim: AxeOSSim) -> dict[str, Any]:
    """Let a test overwrite fields of the ``/api/system/info`` reply (live: change the dict, the next poll sees it)."""
    overrides: dict[str, Any] = {}
    original = sim.info

    def patched() -> dict[str, Any]:
        data = original()
        data.update(overrides)
        return data

    sim.info = patched  # type: ignore[method-assign]
    return overrides


@dataclasses.dataclass
class Miner:
    rig: Rig
    sim: AxeOSSim
    id: str
    host: str
    overrides: dict[str, Any]

    async def poll(self, times: int = 1) -> None:
        for _ in range(times):
            await self.rig.ctx.fleet._poll_once(self.rig.ctx.fleet.runtimes[self.id])

    def unplug(self) -> None:
        del self.rig.hosts[self.host]

    def plug(self) -> None:
        self.rig.hosts[self.host] = self.sim.app()

    async def go_offline(self) -> None:
        self.unplug()
        await self.poll(3)  # three failed polls in a row is what makes a miner 'offline'
        assert self.status == DeviceStatus.OFFLINE

    async def come_back(self) -> None:
        self.plug()
        await self.poll()
        assert self.status == DeviceStatus.ONLINE

    def heat(self, temp_per_w: float) -> None:
        self.sim.profile = dataclasses.replace(self.sim.profile, temp_per_w=temp_per_w)

    @property
    def status(self) -> DeviceStatus:
        return self.rig.ctx.fleet.runtimes[self.id].status

    @property
    def telemetry(self) -> Telemetry:
        t = self.rig.ctx.fleet.runtimes[self.id].telemetry
        assert t is not None
        return t


class Rig:
    def __init__(self, ctx, hosts, tagged, clock) -> None:
        self.ctx = ctx
        self.hosts = hosts
        self.tagged: list[tuple[str, Notification]] = tagged
        self.clock = clock
        self.miners: list[Miner] = []

    @property
    def engine(self) -> AlertEngine:
        return self.ctx.alerts

    @property
    def outbox(self) -> list[Notification]:
        return [n for _, n in self.tagged]

    async def tick(self, advance: float = 0.0) -> None:
        self.clock.t += advance
        await self.engine.tick(self.clock.t)

    async def miner(self, host: str = "g.test", *, name: str | None = None, tags: list[str] | None = None,
                    profile: str = "gamma", up_for_s: float = 7200.0) -> Miner:
        n = len(self.miners)
        sim = AxeOSSim(profile, seed=n + 1, mac=f"AA:BB:CC:00:00:{n + 0x11:02X}")
        sim.started = time.time() - up_for_s  # a miner that has been up a while (fresh boots are exempt from some rules)
        overrides = install_overrides(sim)
        self.hosts[host] = sim.app()
        res = await self.ctx.fleet.add_by_host(host, drivers=["axeos"], name=name, tags=tags)
        m = Miner(self, sim, res.device.id, host, overrides)
        self.miners.append(m)
        await m.poll()
        return m

    def freeze_baselines(self, baselines: dict[str, float] | None = None, fleet: float | None = None) -> None:
        """Pin the 'what is normal' figures. (Left alone, every tick that is more than five minutes after the last
        one would recompute them from history, and with an empty history that clears the fleet baseline.)"""
        self.engine._baselines.update(baselines or {})
        self.engine._fleet_baseline = fleet

        async def keep(now: float) -> None:
            self.engine._baseline_at = now

        self.engine.refresh_baselines = keep  # type: ignore[method-assign]

    def active(self) -> list[dict[str, Any]]:
        return self.engine.active_alerts()

    def titles(self) -> list[str]:
        return [n.title for n in self.outbox]

    async def rule(self, kind: str, **patch: Any) -> AlertRule:
        return await self.engine.update_rule(f"rule_{kind}", patch)

    async def fire(self, advance_to: float) -> None:
        """Tick once to start the clock, then once more after ``advance_to`` seconds."""
        await self.tick()
        await self.tick(advance_to)


@pytest.fixture
async def rig(lan, monkeypatch):
    ctx, hosts = lan
    tagged: list[tuple[str, Notification]] = []

    class Capture(BaseChannel):
        kind = "capture"
        label = "Capture"

        async def send(self, n: Notification) -> None:
            tagged.append((self.config.get("tag", "?"), n))

    monkeypatch.setitem(CHANNEL_CLASSES, "capture", Capture)
    await ctx.store.save_channel(Channel(id="ch_main", kind="capture", name="Main", config={"tag": "main"}))
    await ctx.alerts.ensure_default_rules()
    return Rig(ctx, hosts, tagged, Clock())


async def until(predicate, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError("timed out waiting for the condition")
        await asyncio.sleep(0.01)


# --- the life-cycle: pending -> firing -> reminder -> resolved ---------------------------------------------------------


async def test_device_offline_waits_for_its_duration_before_telling_anyone(rig):
    m = await rig.miner(name="Garage")
    await m.go_offline()
    await rig.tick()
    assert rig.outbox == [] and rig.active() == []  # seen, but not for long enough yet
    await rig.tick(119)
    assert rig.outbox == []
    await rig.tick(1)  # the default is 120 s
    [n] = rig.outbox
    assert n.title == "Garage is offline" and n.severity == Severity.CRITICAL and n.type == "device_offline"
    assert n.device_id == m.id and n.resolved is False
    assert "No answer from g.test" in n.body and "Last error:" in n.body
    assert n.data == {"rule_id": "rule_device_offline"}
    [alert] = rig.active()
    assert alert["title"] == "Garage is offline" and alert["severity"] == "critical" and alert["device_id"] == m.id
    assert alert["rule_id"] == "rule_device_offline" and alert["key"] == f"rule_device_offline:{m.id}"
    assert alert["since"] == rig.clock.t


async def test_a_blip_shorter_than_the_duration_is_never_reported(rig):
    m = await rig.miner()
    await m.go_offline()
    await rig.tick()
    await rig.tick(60)
    await m.come_back()
    await rig.tick(10)
    await rig.tick(600)
    assert rig.outbox == [] and rig.active() == []
    assert rig.engine._tracks == {} and await rig.ctx.store.load_alert_state() == {}


async def test_ticking_again_does_not_repeat_a_firing_alert(rig):
    m = await rig.miner()
    await m.go_offline()
    await rig.fire(120)
    for _ in range(5):
        await rig.tick(30)
    assert len(rig.outbox) == 1


async def test_reminder_after_the_cooldown_then_again_after_the_next_one(rig):
    m = await rig.miner(name="Garage")
    await m.go_offline()
    await rig.fire(120)
    cooldown = RULE_SPECS["device_offline"].cooldown_s  # three hours
    assert cooldown == 3 * 3600
    await rig.tick(cooldown - 1)
    assert len(rig.outbox) == 1
    await rig.tick(1)
    assert len(rig.outbox) == 2
    reminder = rig.outbox[1]
    assert reminder.title == "Still a problem: Garage is offline" and reminder.severity == Severity.CRITICAL
    assert reminder.resolved is False
    await rig.tick(60)  # the reminder restarted the cooldown
    assert len(rig.outbox) == 2
    await rig.tick(cooldown)
    assert len(rig.outbox) == 3
    # the persisted row remembers the first firing and the latest reminder
    [row] = (await rig.ctx.store.load_alert_state()).values()
    assert row["last_notified"] == rig.clock.t and row["since"] < row["last_notified"]


async def test_a_cooldown_of_zero_means_no_reminders(rig):
    m = await rig.miner()
    await rig.rule("device_offline", cooldown_s=0)
    await m.go_offline()
    await rig.fire(120)
    await rig.tick(10 * 24 * 3600)
    assert len(rig.outbox) == 1 and len(rig.active()) == 1


async def test_a_zero_duration_fires_on_the_first_sighting(rig):
    m = await rig.miner()
    await rig.rule("device_offline", params={"for_s": 0})
    await m.go_offline()
    await rig.tick()
    assert len(rig.outbox) == 1


async def test_resolved_message_comes_only_after_the_problem_stays_gone(rig):
    m = await rig.miner(name="Garage")
    await m.go_offline()
    await rig.fire(120)
    await m.come_back()
    await rig.tick(60)  # the first tick that sees it healthy starts the 30 s clear timer
    assert len(rig.outbox) == 1 and len(rig.active()) == 1
    await rig.tick(RESOLVE_AFTER_S - 1)
    assert len(rig.outbox) == 1
    await rig.tick(1)
    assert len(rig.outbox) == 2
    resolved = rig.outbox[1]
    assert resolved.title == "Resolved: Garage is offline" and resolved.severity == Severity.SUCCESS
    assert resolved.resolved is True and resolved.type == "device_offline" and resolved.device_id == m.id
    assert resolved.body == "This problem cleared after 1m 30s."  # 60 s + 30 s after it started firing
    assert rig.active() == [] and rig.engine._tracks == {}
    assert await rig.ctx.store.load_alert_state() == {}
    await rig.tick(3600)
    assert len(rig.outbox) == 2  # nothing more, ever


async def test_a_relapse_during_the_clear_window_neither_resolves_nor_fires_again(rig):
    m = await rig.miner(name="Garage")
    await m.go_offline()
    await rig.fire(120)
    await m.come_back()
    await rig.tick(5)
    await rig.tick(20)  # 20 s into the 30 s clear window ...
    await m.go_offline()  # ... and it drops again
    await rig.tick(5)
    await rig.tick(RESOLVE_AFTER_S + 5)  # the clear timer was reset, and the alert never stopped firing
    assert len(rig.outbox) == 1
    await m.come_back()
    await rig.tick(1)
    await rig.tick(RESOLVE_AFTER_S)
    assert [n.resolved for n in rig.outbox] == [False, True]


async def test_each_device_has_its_own_alert_and_resolves_separately(rig):
    a = await rig.miner("a.test", name="Attic")
    b = await rig.miner("b.test", name="Basement")
    await a.go_offline()
    await rig.tick()
    await rig.tick(60)
    await b.go_offline()
    await rig.tick()  # a: 60 s old, b: just seen
    await rig.tick(60)  # a: 120 s -> fires; b: 60 s -> not yet
    assert rig.titles() == ["Attic is offline"]
    await rig.tick(60)
    assert rig.titles() == ["Attic is offline", "Basement is offline"]
    assert [x["title"] for x in rig.active()] == ["Attic is offline", "Basement is offline"]  # oldest first
    await a.come_back()
    await rig.tick()
    await rig.tick(RESOLVE_AFTER_S)
    assert rig.titles()[-1] == "Resolved: Attic is offline"
    assert [x["title"] for x in rig.active()] == ["Basement is offline"]


async def test_alert_state_is_stored_while_firing_and_cleared_when_resolved(rig):
    m = await rig.miner()
    await m.go_offline()
    await rig.tick()
    assert await rig.ctx.store.load_alert_state() == {}  # pending alerts are not persisted
    await rig.tick(120)
    state = await rig.ctx.store.load_alert_state()
    key = f"rule_device_offline:{m.id}"
    assert set(state) == {key}
    assert state[key]["rule_id"] == "rule_device_offline" and state[key]["device_id"] == m.id
    assert state[key]["since"] == rig.clock.t == state[key]["last_notified"]


def restarted_engine(ctx) -> AlertEngine:
    """What the app builds after a restart: a brand new engine over the same database, with its background loops
    switched off so that the test can drive ticks itself."""
    fresh = AlertEngine(ctx.store, ctx.settings, ctx.bus, ctx.fleet, ctx.network, ctx.notifier)

    async def idle() -> None:
        return None

    fresh._tick_loop = idle  # type: ignore[method-assign]
    fresh._event_loop = idle  # type: ignore[method-assign]
    return fresh


async def test_a_restarted_app_restores_firing_alerts_and_does_not_announce_them_twice(rig):
    ctx = rig.ctx
    m = await rig.miner(name="Garage")
    await m.go_offline()
    await rig.fire(120)
    fired_at = rig.clock.t
    assert len(rig.outbox) == 1

    fresh = restarted_engine(ctx)
    await fresh.start()
    try:
        [track] = fresh._tracks.values()
        assert track.firing and track.since == fired_at and track.last_notified == fired_at
        assert track.cond is not None and track.cond.title == "Garage is offline"  # what the alert said survives a restart
        fresh._baseline_at = rig.clock.t
        await fresh.tick(rig.clock.t + 30)
        assert len(rig.outbox) == 1  # still the original message only
        [alert] = fresh.active_alerts()
        assert alert["title"] == "Garage is offline" and alert["since"] == fired_at  # the condition is back in memory
        # the reminder clock continues from the persisted last_notified, not from the restart
        await fresh.tick(fired_at + RULE_SPECS["device_offline"].cooldown_s)
        assert rig.titles()[-1] == "Still a problem: Garage is offline" and len(rig.outbox) == 2
        [row] = (await ctx.store.load_alert_state()).values()
        assert row["since"] == fired_at and row["last_notified"] == fired_at + RULE_SPECS["device_offline"].cooldown_s
    finally:
        await fresh.stop()


async def test_a_restored_alert_whose_problem_is_gone_is_cleaned_up(rig):
    ctx = rig.ctx
    m = await rig.miner()
    await m.go_offline()
    await rig.fire(120)
    await m.come_back()
    fresh = restarted_engine(ctx)
    await fresh.start()
    try:
        fresh._baseline_at = rig.clock.t
        await fresh.tick(rig.clock.t + 1)
        await fresh.tick(rig.clock.t + 1 + RESOLVE_AFTER_S)
        assert fresh._tracks == {} and fresh.active_alerts() == []
        assert await ctx.store.load_alert_state() == {}
        # the user was told about the problem before the restart, so they must also be told it cleared
        assert rig.titles()[-1].startswith("Resolved:")
    finally:
        await fresh.stop()


# --- scope ---------------------------------------------------------------------------------------------------------


def view(id_: str = "d1", name: str = "Rig", status: DeviceStatus = DeviceStatus.ONLINE, tags: list[str] | None = None,
         **telemetry: Any) -> DeviceView:
    return DeviceView(id=id_, name=name, driver="axeos", family="bitaxe", model="Gamma", host="10.0.0.5", port=80,
                      tags=tags or [], status=status, status_since=900.0, telemetry=Telemetry(**telemetry))


def rule_of(kind: str, **params: Any) -> AlertRule:
    return AlertRule(id=f"r_{kind}", name=kind, kind=kind, params={**RULE_SPECS[kind].defaults(), **params},
                     cooldown_s=RULE_SPECS[kind].cooldown_s)


def eval_ctx(devices: list[DeviceView], *, now: float = 1000.0, network: NetworkState | None = None,
             baselines: dict[str, float] | None = None, fleet_baseline: float | None = None,
             summary: FleetSummary | None = None, settings: Settings | None = None) -> EvalContext:
    return EvalContext(now=now, devices=devices, summary=summary or FleetSummary(), network=network or NetworkState(),
                       settings=settings or Settings(), baselines=baselines or {}, fleet_baseline=fleet_baseline)


@pytest.mark.parametrize(
    ("scope", "matches"),
    [
        ({}, {"a", "b", "c"}),  # an empty scope means everything
        ({"all": True}, {"a", "b", "c"}),
        ({"device_ids": ["b"]}, {"b"}),
        ({"tags": ["rack1"]}, {"a", "b"}),
        ({"device_ids": ["c"], "tags": ["rack1"]}, {"a", "b", "c"}),  # ids and tags add up
        ({"all": True, "tags": ["garage"]}, {"c"}),  # naming something narrows 'all'
        ({"tags": ["nope"]}, set()),
        ({"device_ids": ["nope"]}, set()),
    ],
)
def test_in_scope(scope, matches):
    devices = [view("a", tags=["rack1"]), view("b", tags=["rack1", "rack2"]), view("c", tags=["garage"])]
    rule = AlertRule(id="r", name="r", kind="device_offline", scope=scope)
    assert {d.id for d in devices if in_scope(rule, d)} == matches


async def test_a_rule_scoped_to_some_miners_ignores_the_others(rig):
    a = await rig.miner("a.test", name="Attic", tags=["rack1"])
    b = await rig.miner("b.test", name="Basement", tags=["rack2"])
    await a.go_offline()
    await b.go_offline()
    for scope, expected in (
        ({"device_ids": [a.id]}, ["Attic is offline"]),
        ({"tags": ["rack2"]}, ["Basement is offline"]),
        ({"all": True}, ["Attic is offline", "Basement is offline"]),
        ({"device_ids": [a.id], "tags": ["rack2"]}, ["Attic is offline", "Basement is offline"]),
        ({"tags": ["rack3"]}, []),
    ):
        rig.tagged.clear()
        rig.engine._tracks.clear()
        await rig.rule("device_offline", scope=scope)
        await rig.fire(120)
        assert sorted(rig.titles()) == expected, scope


async def test_narrowing_the_scope_of_a_firing_alert_resolves_it(rig):
    a = await rig.miner("a.test", name="Attic", tags=["rack1"])
    await a.go_offline()
    await rig.fire(120)
    assert len(rig.active()) == 1
    await rig.rule("device_offline", scope={"tags": ["rack9"]})  # the miner is no longer covered by the rule
    await rig.tick(1)
    await rig.tick(RESOLVE_AFTER_S)
    assert rig.titles() == ["Attic is offline", "Resolved: Attic is offline"] and rig.active() == []


# --- the built-in rules, end to end through simulated miners ----------------------------------------------------------


async def test_temp_high_fires_after_its_duration_with_the_numbers_in_the_message(rig):
    m = await rig.miner(name="Garage")
    m.heat(2.4)
    await m.poll()
    assert 75 <= m.telemetry.temp_asic_c < 85  # hot, but short of the critical line
    await rig.tick()
    await rig.tick(59)
    assert rig.outbox == []
    await rig.tick(1)
    [n] = rig.outbox
    assert n.title == "Garage is running hot" and n.severity == Severity.WARNING and n.type == "temp_high"
    assert n.body.startswith("ASIC ") and "(limit 75)" in n.body and n.body.endswith("Check airflow and the fan.")
    assert "voltage regulator" not in n.body


async def test_temp_high_escalates_to_critical_at_the_critical_threshold(rig):
    m = await rig.miner(name="Garage")
    m.heat(3.2)
    await m.poll()
    assert m.telemetry.temp_asic_c >= 85
    await rig.fire(60)
    [n] = rig.outbox
    assert n.severity == Severity.CRITICAL and rig.active()[0]["severity"] == "critical"
    # the critical line comes from Settings > alerts, not from the rule
    rig.tagged.clear()
    rig.engine._tracks.clear()
    await rig.ctx.settings.update({"alerts": {"temp_crit_c": 100}})
    await rig.fire(60)
    assert rig.outbox[0].severity == Severity.WARNING


async def test_temp_high_also_watches_the_voltage_regulator(rig):
    m = await rig.miner(name="Garage")
    assert m.telemetry.temp_vr_c < 60
    await rig.rule("temp_high", params={"asic_c": 120, "vr_c": 45})  # ASIC limit out of reach, regulator limit low
    await rig.fire(60)
    [n] = rig.outbox
    assert n.body.startswith("voltage regulator ") and "(limit 45)" in n.body and "ASIC" not in n.body


async def test_temp_high_stays_quiet_for_a_cool_miner_and_for_an_offline_one(rig):
    await rig.miner("cool.test", name="Cool")
    hot = await rig.miner("hot.test", name="Hot")
    hot.heat(3.2)
    await hot.poll()
    await hot.go_offline()  # its last reading was hot, but an unreachable miner is a different problem
    await rig.fire(600)
    assert rig.titles() == ["Hot is offline"]


async def test_a_custom_rule_with_a_lower_limit_fires_while_the_builtin_does_not(rig):
    m = await rig.miner(name="Garage")
    m.heat(1.9)
    await m.poll()
    assert 65 < m.telemetry.temp_asic_c < 75
    custom = await rig.engine.create_rule({"kind": "temp_high", "name": "Cooler limit", "params": {"asic_c": 65, "for_s": 0}})
    await rig.tick()
    [n] = rig.outbox
    assert n.type == "temp_high" and "(limit 65)" in n.body and n.data["rule_id"] == custom.id
    [alert] = rig.active()
    assert alert["rule_id"] == custom.id  # the 75 degree builtin stayed silent


async def test_fan_failure(rig):
    m = await rig.miner(name="Garage")
    m.overrides["fanrpm"] = 0
    await m.poll()
    assert m.telemetry.fan_pct >= 20 and m.telemetry.temp_asic_c >= 45
    await rig.tick()
    await rig.tick(59)
    assert rig.outbox == []
    await rig.tick(1)
    [n] = rig.outbox
    assert n.title == "Garage: the fan is not spinning" and n.severity == Severity.CRITICAL and n.type == "fan_failure"
    assert "reads 0 rpm" in n.body and "Stop the miner if this continues." in n.body


@pytest.mark.parametrize(
    "overrides",
    [{"fanrpm": 120}, {"fanrpm": 0, "fanspeed": 10}, {"fanrpm": 0, "temp": 40.0, "vrTemp": 38.0}, {"fanrpm": 0, "miningPaused": True}],
    ids=["spinning", "not-asked-to-spin", "chip-is-cold", "paused"],
)
async def test_fan_failure_needs_all_of_its_conditions(rig, overrides):
    m = await rig.miner()
    m.overrides.update(overrides)
    await m.poll()
    await rig.fire(600)
    assert [n for n in rig.outbox if n.type == "fan_failure"] == []


async def test_reject_rate_high_names_the_most_common_reason(rig):
    m = await rig.miner(name="Garage")
    m.overrides.update(
        sharesAccepted=900, sharesRejected=100,
        sharesRejectedReasons=[{"message": "Duplicate share", "count": 30}, {"message": "Job not found", "count": 70}],
    )
    await m.poll()
    await rig.tick()
    await rig.tick(599)
    assert rig.outbox == []
    await rig.tick(1)
    [n] = rig.outbox
    assert n.title == "Garage: 10.0% of shares are rejected" and n.type == "reject_rate_high"
    assert n.body == ("100 of 1000 shares were rejected. Most common reason: Job not found (70). "
                      "A weak WiFi signal is the usual cause.")


@pytest.mark.parametrize(
    ("accepted", "rejected", "params", "fires"),
    [
        (900, 100, {}, True),
        (950, 50, {}, True),  # exactly 5 % of 1000 shares
        (960, 40, {}, False),  # 4 %
        (100, 20, {}, False),  # 16.7 %, but fewer than 200 shares: too little data to judge
        (100, 20, {"min_shares": 50}, True),
        (900, 100, {"pct": 15}, False),
    ],
)
async def test_reject_rate_thresholds(rig, accepted, rejected, params, fires):
    m = await rig.miner()
    m.overrides.update(sharesAccepted=accepted, sharesRejected=rejected)
    await m.poll()
    if params:
        await rig.rule("reject_rate_high", params=params)
    await rig.fire(600)
    assert any(n.type == "reject_rate_high" for n in rig.outbox) is fires


async def test_pool_fallback_fires_and_names_the_pool_the_miner_switched_to(rig):
    m = await rig.miner(name="Garage")
    m.overrides["isUsingFallbackStratum"] = 1
    await m.poll()
    assert m.status == DeviceStatus.DEGRADED
    await rig.tick()
    await rig.tick(119)
    assert rig.outbox == []
    await rig.tick(1)
    [n] = rig.outbox
    assert n.title == "Garage is using its fallback pool" and n.type == "pool_fallback" and n.severity == Severity.WARNING
    assert "solo.ckpool.org:3333" in n.body
    # back on the primary pool: the alert resolves
    m.overrides["isUsingFallbackStratum"] = 0
    await m.poll()
    await rig.tick()
    await rig.tick(RESOLVE_AFTER_S)
    assert rig.titles()[-1] == "Resolved: Garage is using its fallback pool"


async def test_hashrate_drop_compares_against_the_miners_own_baseline(rig):
    m = await rig.miner(name="Garage")
    rig.freeze_baselines({m.id: 2.0e12})  # it normally does 2 TH/s; the simulator delivers about 1.15
    await rig.tick()
    await rig.tick(599)
    assert rig.outbox == []
    await rig.tick(1)
    [n] = rig.outbox
    assert n.type == "hashrate_drop" and n.severity == Severity.WARNING
    assert n.title.startswith("Garage: hashrate is down ") and n.title.endswith("%")
    assert 38 <= int(n.title.split("down ")[1].rstrip("%")) <= 48
    assert "it normally does about 2.00 TH/s." in n.body and "It is doing 1." in n.body


@pytest.mark.parametrize(
    ("baseline", "params", "fires"),
    [(2.0e12, {}, True), (1.3e12, {}, False), (1.4e12, {"drop_pct": 10}, True), (None, {}, False)],
    ids=["well-below", "within-tolerance", "stricter-rule", "no-baseline-yet"],
)
async def test_hashrate_drop_thresholds(rig, baseline, params, fires):
    m = await rig.miner()
    rig.freeze_baselines({m.id: baseline} if baseline else {})
    if params:
        await rig.rule("hashrate_drop", params=params)
    await rig.fire(600)
    assert any(n.type == "hashrate_drop" for n in rig.outbox) is fires


async def test_hashrate_drop_ignores_a_freshly_rebooted_miner(rig):
    m = await rig.miner(up_for_s=60)  # still ramping up after a reboot
    rig.freeze_baselines({m.id: 5.0e12})
    await rig.fire(600)
    assert rig.outbox == []
    m.sim.started = time.time() - 3600  # an hour later it is expected to be at full speed
    await m.poll()
    await rig.fire(600)
    assert [n.type for n in rig.outbox] == ["hashrate_drop"]


async def test_hashrate_drop_ignores_paused_and_offline_miners(rig):
    m = await rig.miner()
    rig.freeze_baselines({m.id: 5.0e12})
    m.overrides["miningPaused"] = True
    await m.poll()
    assert m.status == DeviceStatus.PAUSED
    await rig.fire(600)
    assert rig.outbox == []
    m.overrides.clear()
    await m.go_offline()
    await rig.fire(600)
    assert [n.type for n in rig.outbox] == ["device_offline"]


async def test_baselines_are_the_median_of_recent_history_and_feed_the_alert(rig):
    ctx = rig.ctx
    m = await rig.miner(name="Garage")
    now = rig.clock.t
    # 8 normal samples of 10 TH/s, one dead period (0) and one half-dead one, spaced 5 minutes apart
    levels = [10e12] * 8 + [0.0, 1e12]
    rows = [telemetry_to_row(m.id, Telemetry(ts=now - 700 - 300 * i, hashrate_hs=v)) for i, v in enumerate(levels)]
    await ctx.store.samples.write(rows)
    assert rig.engine._baselines == {} and rig.engine._baseline_at == 0.0
    await rig.tick()  # the first tick works out what is normal
    assert rig.engine._baseline_at == now
    assert rig.engine._baselines[m.id] == pytest.approx(10e12)  # the median shrugs off the outage; a mean would say 8.1
    assert rig.engine._fleet_baseline == pytest.approx(10e12)
    await rig.tick(599)
    assert rig.outbox == []
    await rig.tick(1)  # the simulator does ~1.15 TH/s against a 10 TH/s baseline
    assert [n.type for n in rig.outbox] == ["hashrate_drop"]
    # baselines are only refreshed every five minutes
    rig.engine._baselines[m.id] = 123.0
    await rig.tick(100)
    assert rig.engine._baselines[m.id] == 123.0
    await rig.tick(250)
    assert rig.engine._baselines[m.id] == pytest.approx(10e12)
    assert [n.type for n in rig.outbox] == ["hashrate_drop"]  # and none of that produced extra messages


async def test_baselines_need_at_least_six_populated_intervals(rig):
    m = await rig.miner()
    now = rig.clock.t
    rows = [telemetry_to_row(m.id, Telemetry(ts=now - 700 - 300 * i, hashrate_hs=9e12)) for i in range(5)]
    await rig.ctx.store.samples.write(rows)
    await rig.engine.refresh_baselines(now)
    assert rig.engine._baselines == {} and rig.engine._fleet_baseline is None


async def test_thin_history_does_not_erase_a_baseline_already_learned(rig):
    """After a data purge or a short outage of the recorder there may be < 6 points; keep what we knew."""
    m = await rig.miner()
    now = rig.clock.t
    rows = [telemetry_to_row(m.id, Telemetry(ts=now - 700 - 300 * i, hashrate_hs=9e12)) for i in range(8)]
    await rig.ctx.store.samples.write(rows)
    await rig.engine.refresh_baselines(now)
    assert rig.engine._fleet_baseline == pytest.approx(9e12)
    await rig.ctx.store.samples.delete_device_samples(m.id)  # history is gone
    await rig.engine.refresh_baselines(now + 600)
    assert rig.engine._fleet_baseline == pytest.approx(9e12)  # still the last good value, not None


async def test_fleet_hashrate_drop_is_off_by_default_and_uses_the_fleet_baseline(rig):
    await rig.miner("a.test")
    await rig.miner("b.test")
    rig.freeze_baselines(fleet=8.0e12)  # the two simulated miners deliver about 2.3 TH/s
    await rig.fire(600)
    assert rig.outbox == []  # the rule exists but is disabled
    await rig.rule("fleet_hashrate_drop", enabled=True)
    await rig.fire(600)
    [n] = rig.outbox
    assert n.type == "fleet_hashrate_drop" and n.device_id is None
    assert n.title.startswith("Total hashrate is down ") and "it normally does about 8.00 TH/s" in n.body
    assert rig.active()[0]["key"] == "rule_fleet_hashrate_drop:fleet"


@pytest.mark.parametrize("fleet_baseline", [None, 0.0, 1.3e12], ids=["unknown", "zero", "close-to-normal"])
async def test_fleet_hashrate_drop_needs_a_baseline_and_a_real_drop(rig, fleet_baseline):
    await rig.miner()
    await rig.rule("fleet_hashrate_drop", enabled=True)
    rig.freeze_baselines(fleet=fleet_baseline)
    await rig.fire(600)
    assert rig.outbox == []


async def test_device_attention_is_off_by_default_and_ignores_a_restart_in_progress(rig):
    m = await rig.miner(name="Garage")
    m.overrides["isStratumConnected"] = 0
    await m.poll()
    assert m.status == DeviceStatus.DEGRADED
    await rig.fire(600)
    assert rig.outbox == []  # disabled by default
    await rig.rule("device_attention", enabled=True)
    await rig.tick()
    await rig.tick(179)
    assert rig.outbox == []
    await rig.tick(1)
    [n] = rig.outbox
    assert n.title == "Garage needs attention" and n.body == "Not connected to its pool" and n.type == "device_attention"


async def test_device_attention_does_not_fire_while_a_miner_restarts_on_purpose(rig):
    m = await rig.miner(name="Garage")
    await rig.rule("device_attention", enabled=True)
    out = await rig.ctx.fleet.run_action(m.id, "restart", actor="test")
    assert out["ok"]
    m.unplug()
    await m.poll(4)
    rt = rig.ctx.fleet.runtimes[m.id]
    assert rt.status == DeviceStatus.DEGRADED and rt.status_reason == "Restarting"
    await rig.fire(600)
    assert rig.outbox == []  # neither 'offline' nor 'needs attention': it was told to restart


# --- node / pool rules (driven by a NetworkState with SourceHealth entries) ----------------------------------------------------


def health(id_: str = "n1", kind: str = "bitcoin_core", name: str = "My node", ok: bool | None = False,
           error: str | None = "connection refused", implicit: bool = False) -> SourceHealth:
    return SourceHealth(id=id_, kind=kind, name=name, ok=ok, error=error, implicit=implicit)


async def test_node_down_fires_after_three_minutes_and_resolves_when_it_answers(rig):
    rig.ctx.network.state = NetworkState(sources=[health()])
    await rig.tick()
    await rig.tick(179)
    assert rig.outbox == []
    await rig.tick(1)
    [n] = rig.outbox
    assert n.title == "Can't reach My node" and n.body == "connection refused" and n.type == "node_down"
    assert n.severity == Severity.WARNING and n.device_id is None
    assert rig.active()[0]["key"] == "rule_node_down:n1"
    rig.ctx.network.state = NetworkState(sources=[health(ok=True, error=None)])
    await rig.tick()
    await rig.tick(RESOLVE_AFTER_S)
    assert rig.titles() == ["Can't reach My node", "Resolved: Can't reach My node"]


@pytest.mark.parametrize(
    "source",
    [
        health(kind="mempool_space", name="mempool.space"),  # public data is not 'your node'
        health(implicit=True),  # built-in sources never alarm
        health(ok=None, error=None),  # not polled yet
        health(ok=True, error=None),
    ],
    ids=["public-data", "implicit", "not-polled-yet", "healthy"],
)
async def test_node_down_ignores_sources_that_do_not_count(rig, source):
    rig.ctx.network.state = NetworkState(sources=[source])
    await rig.fire(3600)
    assert rig.outbox == []


@pytest.mark.parametrize("kind", ["bitcoin_core", "public_pool", "ckpool"])
async def test_node_down_covers_nodes_and_pools(rig, kind):
    rig.ctx.network.state = NetworkState(sources=[health(kind=kind, name=f"My {kind}", error=None)])
    await rig.fire(180)
    [n] = rig.outbox
    assert n.title == f"Can't reach My {kind}" and n.body == "No answer."  # no error text yet


async def test_node_down_tracks_every_source_separately(rig):
    rig.ctx.network.state = NetworkState(sources=[health("n1", name="Node A"), health("p1", "public_pool", "Pool B", error="timed out")])
    await rig.fire(180)
    assert sorted(rig.titles()) == ["Can't reach Node A", "Can't reach Pool B"]


@pytest.mark.parametrize(("behind", "params", "fires"), [(5, {}, True), (4, {}, True), (3, {}, False), (0, {}, False), (None, {}, False),
                                                        (2, {"blocks": 1}, True), (1, {"blocks": 1}, False)])
async def test_node_behind_threshold(rig, behind, params, fires):
    if params:
        await rig.rule("node_behind", params=params)
    rig.ctx.network.state = NetworkState(node_behind_by=behind)
    await rig.tick()
    await rig.tick(599)
    assert rig.outbox == []
    await rig.tick(1)
    assert [n.type for n in rig.outbox] == (["node_behind"] if fires else [])
    if fires:
        assert rig.outbox[0].title == f"Your node is {behind} blocks behind"


async def test_node_behind_does_not_repeat_when_the_gap_changes(rig):
    rig.ctx.network.state = NetworkState(node_behind_by=5)
    await rig.fire(600)
    rig.ctx.network.state = NetworkState(node_behind_by=9)
    await rig.tick(60)
    assert len(rig.outbox) == 1
    rig.ctx.network.state = NetworkState(node_behind_by=0)
    await rig.tick()
    await rig.tick(RESOLVE_AFTER_S)
    # the 'resolved' message describes the problem as it was last seen
    assert rig.titles() == ["Your node is 5 blocks behind", "Resolved: Your node is 9 blocks behind"]


# --- disabled / deleted rules ---------------------------------------------------------------------------------------------------


async def test_a_disabled_rule_does_nothing(rig):
    m = await rig.miner()
    await m.go_offline()
    await rig.rule("device_offline", enabled=False)
    await rig.fire(3600)
    assert rig.outbox == [] and rig.active() == [] and rig.engine._tracks == {}


async def test_disabling_a_firing_rule_silences_and_forgets_it(rig):
    m = await rig.miner()
    await m.go_offline()
    await rig.fire(120)
    assert len(rig.active()) == 1 and len(await rig.ctx.store.load_alert_state()) == 1
    await rig.rule("device_offline", enabled=False)
    assert rig.active() == [] and await rig.ctx.store.load_alert_state() == {}
    await rig.tick(3600)
    assert len(rig.outbox) == 1  # no 'resolved' message: the user turned the rule off, nothing was fixed
    # turning it back on starts from scratch: the full duration has to pass again
    await rig.rule("device_offline", enabled=True)
    await rig.tick()
    await rig.tick(119)
    assert len(rig.outbox) == 1
    await rig.tick(1)
    assert len(rig.outbox) == 2


async def test_a_rule_switched_off_behind_the_engines_back_is_dropped_on_the_next_tick(rig):
    m = await rig.miner()
    await m.go_offline()
    await rig.fire(120)
    stored = await rig.ctx.store.get_rule("rule_device_offline")
    stored.enabled = False
    await rig.ctx.store.save_rule(stored)  # e.g. a config import, not update_rule()
    await rig.tick(1)
    assert rig.active() == [] and await rig.ctx.store.load_alert_state() == {}
    assert len(rig.outbox) == 1


async def test_a_deleted_rule_takes_its_alerts_with_it(rig):
    m = await rig.miner()
    await m.go_offline()
    await rig.fire(120)
    await rig.ctx.store.delete_rule("rule_device_offline")
    await rig.tick(1)
    assert rig.active() == [] and len(rig.outbox) == 1


async def test_a_buggy_rule_cannot_stop_the_others(rig, monkeypatch):
    down = await rig.miner("down.test", name="Down")
    hot = await rig.miner("hot.test", name="Hot")
    hot.heat(3.2)
    await hot.poll()
    await down.go_offline()

    real_evaluator = EVALUATORS["temp_high"]

    def boom(rule, ctx):
        raise RuntimeError("bug in an evaluator")

    monkeypatch.setitem(EVALUATORS, "temp_high", boom)
    await rig.fire(120)  # temp_high blows up on every tick; device_offline carries on regardless
    assert [n.type for n in rig.outbox] == ["device_offline"]
    # without the bug the same fleet would have produced the temperature alert too
    monkeypatch.setitem(EVALUATORS, "temp_high", real_evaluator)
    rig.tagged.clear()
    await rig.rule("temp_high", params={"for_s": 0})
    await rig.tick()
    assert [n.type for n in rig.outbox] == ["temp_high"]


# --- routing: which channels hear about what ----------------------------------------------------------------------------------------


async def test_a_rule_can_be_limited_to_specific_channels(rig):
    await rig.ctx.store.save_channel(Channel(id="ch_other", kind="capture", name="Other", config={"tag": "other"}))
    m = await rig.miner()
    await m.go_offline()
    await rig.rule("device_offline", channel_ids=["ch_other"])
    await rig.fire(120)
    assert [tag for tag, _ in rig.tagged] == ["other"]
    rig.tagged.clear()
    rig.engine._tracks.clear()
    await rig.rule("device_offline", channel_ids=[])  # empty = every enabled channel
    await rig.fire(120)
    assert sorted(tag for tag, _ in rig.tagged) == ["main", "other"]


# --- tick side effects ---------------------------------------------------------------------------------------------------------------


async def test_every_tick_publishes_the_active_alerts_on_the_bus(rig):
    sub = rig.ctx.bus.subscribe({"alerts"})
    m = await rig.miner(name="Garage")
    await m.go_offline()
    await rig.tick()
    await rig.tick(120)
    messages = []
    while not sub.queue.empty():
        messages.append(sub.queue.get_nowait())
    sub.close()
    assert len(messages) == 2 and all(msg.topic == "alerts" for msg in messages)
    assert messages[0].data == {"active": []}
    [alert] = messages[1].data["active"]
    assert alert["title"] == "Garage is offline"


# --- event rules ----------------------------------------------------------------------------------------------------------------------


@pytest.fixture
def event_time(monkeypatch):
    """Give the alert module its own, controllable clock for event cooldowns."""
    clock = Clock()
    monkeypatch.setattr(alerts_mod, "time", SimpleNamespace(time=lambda: clock.t))
    return clock


def best_share(device_id: str | None = "dev_1", **extra: Any) -> dict[str, Any]:
    return {"type": "new_best_share", "title": "New best share on Gamma", "body": "Difficulty 2G (was 1G).",
            "device_id": device_id, "severity": "success", "data": {"difficulty": 2e9, "previous": 1e9}, **extra}


async def test_new_best_share_event_becomes_a_notification(rig):
    await rig.engine.handle_event(best_share())
    [n] = rig.outbox
    assert n.title == "New best share on Gamma" and n.body == "Difficulty 2G (was 1G)."
    assert n.severity == Severity.SUCCESS and n.type == "new_best_share" and n.device_id == "dev_1"
    assert n.data == {"difficulty": 2e9, "previous": 1e9} and n.resolved is False


async def test_event_cooldown_is_per_device(rig, event_time):
    engine = rig.engine
    await engine.handle_event(best_share("dev_1"))
    await engine.handle_event(best_share("dev_1"))  # same device, same instant: swallowed
    await engine.handle_event(best_share("dev_2"))  # a different device has its own cooldown
    assert [n.device_id for n in rig.outbox] == ["dev_1", "dev_2"]
    event_time.t += 299
    await engine.handle_event(best_share("dev_1"))
    assert len(rig.outbox) == 2
    event_time.t += 1  # the 300 s cooldown has passed
    await engine.handle_event(best_share("dev_1"))
    assert [n.device_id for n in rig.outbox] == ["dev_1", "dev_2", "dev_1"]


async def test_events_without_a_device_share_one_cooldown(rig, event_time):
    await rig.engine.handle_event(best_share(None))
    await rig.engine.handle_event(best_share(None))
    assert len(rig.outbox) == 1


async def test_block_found_is_never_rate_limited(rig, event_time):
    ev = {"type": "block_found", "title": "YOU FOUND A BLOCK!", "body": "Block 972,176 paid 3.1500 BTC.", "device_id": None,
          "data": {"height": 972176}}
    for _ in range(3):
        await rig.engine.handle_event(ev)
    assert len(rig.outbox) == 3
    assert all(n.type == "block_found" and n.severity == Severity.SUCCESS for n in rig.outbox)
    assert rig.outbox[0].data == {"height": 972176}


async def test_an_event_nobody_subscribed_to_is_ignored(rig):
    await rig.engine.handle_event({"type": "device_online", "title": "x"})
    await rig.engine.handle_event({"type": "nonsense", "title": "x"})
    await rig.engine.handle_event({"title": "no type at all"})
    assert rig.outbox == []


@pytest.mark.parametrize("kind", ["device_restarted", "difficulty_adjusted", "firmware_changed"])
async def test_off_by_default_event_rules_speak_up_once_enabled(rig, kind):
    ev = {"type": kind, "title": f"something: {kind}", "device_id": "dev_1"}
    await rig.engine.handle_event(ev)
    assert rig.outbox == []
    await rig.rule(kind, enabled=True)
    await rig.engine.handle_event(ev)
    [n] = rig.outbox
    assert n.type == kind and n.severity == Severity.INFO and n.title == f"something: {kind}" and n.body == ""


async def test_event_rules_use_the_rules_severity_name_fallbacks_and_channels(rig):
    await rig.ctx.store.save_channel(Channel(id="ch_other", kind="capture", name="Other", config={"tag": "other"}))
    await rig.rule("new_best_share", severity="critical", channel_ids=["ch_other"])
    await rig.engine.handle_event({"type": "new_best_share", "device_id": "dev_9"})  # no title, no body
    [(tag, n)] = rig.tagged
    assert tag == "other" and n.severity == Severity.CRITICAL
    assert n.title == RULE_SPECS["new_best_share"].label and n.body == ""


async def test_a_disabled_event_rule_stays_silent(rig):
    await rig.rule("new_best_share", enabled=False)
    await rig.engine.handle_event(best_share())
    assert rig.outbox == []


async def test_events_reach_the_engine_through_the_event_log(rig):
    ctx = rig.ctx
    await ctx.alerts.start()
    try:
        await until(lambda: ctx.bus.subscriber_count >= 1)  # the engine's event loop is listening
        await ctx.events.emit("device_online", "not an alert rule", device_id="dev_1")
        await ctx.events.emit("new_best_share", "New best share on Gamma", severity=Severity.SUCCESS, body="Difficulty 2G (was 1G).",
                              device_id="dev_1", data={"difficulty": 2e9})
        await until(lambda: rig.outbox)
    finally:
        await ctx.alerts.stop()
    [n] = rig.outbox
    assert n.type == "new_best_share" and n.title == "New best share on Gamma" and n.data == {"difficulty": 2e9}


class QuickAsyncio:
    """The ``asyncio`` module as the alert engine sees it, with its ten second pauses shortened to a few milliseconds."""

    def __getattr__(self, name: str) -> Any:
        return getattr(asyncio, name)

    @staticmethod
    async def sleep(seconds: float) -> None:
        await asyncio.sleep(0.005)


async def test_a_tick_that_blows_up_does_not_end_the_background_loop(rig, monkeypatch):
    engine = rig.engine
    calls: list[float] = []
    real_tick = engine.tick

    async def flaky(now: float) -> None:
        calls.append(now)
        if len(calls) == 1:
            raise RuntimeError("the database hiccuped")
        await real_tick(now)

    monkeypatch.setattr(engine, "tick", flaky)
    monkeypatch.setattr(alerts_mod, "asyncio", QuickAsyncio())
    await engine.start()
    try:
        await until(lambda: len(calls) >= 3)  # it kept evaluating after the failure
        assert not engine._tasks[0].done()
    finally:
        await engine.stop()
    assert all(t.done() for t in engine._tasks)


async def test_an_event_that_cannot_be_handled_does_not_end_the_event_loop(rig, monkeypatch):
    engine = rig.engine
    real_handle = engine.handle_event
    seen: list[str | None] = []

    async def flaky(ev: dict[str, Any]) -> None:
        seen.append(ev.get("device_id"))
        if len(seen) == 1:
            raise RuntimeError("cannot handle this one")
        await real_handle(ev)

    monkeypatch.setattr(engine, "handle_event", flaky)
    await engine.start()
    try:
        await until(lambda: rig.ctx.bus.subscriber_count >= 1)
        await rig.ctx.events.emit("new_best_share", "first", device_id="dev_1")
        await rig.ctx.events.emit("new_best_share", "second", device_id="dev_2")
        await until(lambda: len(rig.outbox) == 2, timeout=5)
    finally:
        await engine.stop()
    assert seen == ["dev_1", "dev_1", "dev_2"] and [n.title for n in rig.outbox] == ["first", "second"]


async def test_baselines_survive_a_history_query_that_fails(rig, monkeypatch):
    rig.engine._baselines["dev_1"] = 5e12
    rig.engine._fleet_baseline = 5e12

    async def broken(**kwargs: Any) -> None:
        raise ValueError("end must be after start")

    monkeypatch.setattr(rig.ctx.store.samples, "history", broken)
    await rig.engine.refresh_baselines(rig.clock.t)  # must not raise
    assert rig.engine._baseline_at == rig.clock.t
    assert rig.engine._baselines == {"dev_1": 5e12} and rig.engine._fleet_baseline == 5e12


async def test_a_started_engine_evaluates_state_rules_on_its_own_loop(rig):
    ctx = rig.ctx
    m = await rig.miner(name="Garage")
    await m.go_offline()
    await rig.rule("device_offline", params={"for_s": 0})
    await ctx.alerts.start()
    try:
        await until(lambda: rig.outbox)
    finally:
        await ctx.alerts.stop()
    assert rig.titles() == ["Garage is offline"]
    assert ctx.alerts._tasks and all(t.done() for t in ctx.alerts._tasks)


# --- rule management ---------------------------------------------------------------------------------------------------------------------


async def test_default_rules_are_created_once_and_respect_user_changes(rig):
    store = rig.ctx.store
    rules = {r.kind: r for r in await store.list_rules()}
    assert set(rules) == set(RULE_SPECS) and all(r.builtin and r.id == f"rule_{r.kind}" for r in rules.values())
    for kind, spec in RULE_SPECS.items():
        r = rules[kind]
        assert (r.enabled, r.severity, r.cooldown_s, r.params) == (spec.enabled_by_default, spec.severity, spec.cooldown_s, spec.defaults())
    assert {k for k, r in rules.items() if not r.enabled} == {"fleet_hashrate_drop", "device_attention", "device_restarted",
                                                             "difficulty_adjusted", "firmware_changed"}
    await rig.rule("temp_high", enabled=False, params={"asic_c": 70})
    await rig.engine.ensure_default_rules()  # e.g. on the next start-up
    again = {r.kind: r for r in await store.list_rules()}
    assert len(again) == len(rules)
    assert again["temp_high"].enabled is False and again["temp_high"].params["asic_c"] == 70


async def test_create_rule_fills_in_the_defaults_of_its_type(rig):
    rule = await rig.engine.create_rule({"kind": "temp_high", "name": "Cooler limit", "params": {"asic_c": 65}})
    assert rule.id.startswith("rule_") and rule.builtin is False and rule.enabled is True
    assert rule.name == "Cooler limit" and rule.kind == "temp_high"
    assert rule.params == {"asic_c": 65, "vr_c": 90, "for_s": 60}  # the rest comes from the spec
    assert (rule.severity, rule.cooldown_s, rule.scope, rule.channel_ids) == (Severity.WARNING, 1800, {"all": True}, [])
    stored = await rig.ctx.store.get_rule(rule.id)
    assert stored is not None and stored.model_dump() == rule.model_dump()


async def test_create_rule_accepts_every_option(rig):
    rule = await rig.engine.create_rule({
        "kind": "device_offline", "enabled": False, "severity": "critical", "scope": {"tags": ["rack1"]},
        "params": {"for_s": 30}, "channel_ids": ["ch_main"], "cooldown_s": 60,
    })
    assert rule.name == RULE_SPECS["device_offline"].label  # unnamed rules get the type's label
    assert (rule.enabled, rule.severity, rule.scope, rule.params, rule.channel_ids, rule.cooldown_s) == (
        False, Severity.CRITICAL, {"tags": ["rack1"]}, {"for_s": 30}, ["ch_main"], 60.0)


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"kind": "teleport"}, "unknown rule type 'teleport'"),
        ({}, "unknown rule type None"),
        ({"kind": "temp_high", "params": {"asic_c": 999}}, "ASIC limit must be between 40 and 120"),
        ({"kind": "temp_high", "params": {"asic_c": "hot"}}, "ASIC limit must be a number"),
        ({"kind": "temp_high", "cooldown_s": -1}, "cooldown cannot be negative"),
        ({"kind": "temp_high", "severity": "urgent"}, "'urgent' is not a valid Severity"),
    ],
)
async def test_create_rule_rejects_bad_input_and_saves_nothing(rig, data, message):
    before = len(await rig.ctx.store.list_rules())
    with pytest.raises(ValueError, match=message):
        await rig.engine.create_rule(data)
    assert len(await rig.ctx.store.list_rules()) == before


async def test_update_rule_changes_only_what_is_sent(rig):
    updated = await rig.engine.update_rule("rule_temp_high", {
        "name": "Hot!", "enabled": False, "scope": {"tags": ["x"]}, "channel_ids": ["ch_main"], "cooldown_s": 99, "severity": "critical",
        "params": {"asic_c": 70},
    })
    assert (updated.name, updated.enabled, updated.scope, updated.channel_ids, updated.cooldown_s, updated.severity) == (
        "Hot!", False, {"tags": ["x"]}, ["ch_main"], 99, Severity.CRITICAL)
    assert updated.params == {"asic_c": 70, "vr_c": 90, "for_s": 60}  # params merge, they do not replace
    stored = await rig.ctx.store.get_rule("rule_temp_high")
    assert stored.model_dump() == updated.model_dump()
    untouched = await rig.engine.update_rule("rule_temp_high", {})
    assert untouched.model_dump() == updated.model_dump()


async def test_update_rule_cannot_change_the_type_or_build_in_status(rig):
    r = await rig.engine.update_rule("rule_temp_high", {"kind": "fan_failure", "builtin": False, "id": "other"})
    assert (r.kind, r.builtin, r.id) == ("temp_high", True, "rule_temp_high")


async def test_update_rule_validates_before_saving(rig):
    with pytest.raises(ValueError, match="ASIC limit must be between 40 and 120"):
        await rig.engine.update_rule("rule_temp_high", {"params": {"asic_c": 999}, "name": "should not be saved"})
    stored = await rig.ctx.store.get_rule("rule_temp_high")
    assert stored.params["asic_c"] == 75 and stored.name == RULE_SPECS["temp_high"].label
    with pytest.raises(ValueError):
        await rig.engine.update_rule("rule_temp_high", {"severity": "urgent"})
    with pytest.raises(KeyError):
        await rig.engine.update_rule("rule_nope", {"enabled": False})


# --- validation and the rule catalogue -------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "ok"),
    [(39.9, False), (40, True), (75, True), (120, True), (120.1, False), ("65", True), (None, True)],
)
def test_validate_rule_bounds_are_inclusive(value, ok):
    rule = AlertRule(id="r", name="r", kind="temp_high", params={"asic_c": value})
    if ok:
        validate_rule(rule)
    else:
        with pytest.raises(ValueError, match=r"ASIC limit must be between 40 and 120"):
            validate_rule(rule)


def test_validate_rule_rejects_unknown_types_non_numbers_and_negative_cooldowns():
    with pytest.raises(ValueError, match=r"unknown rule type 'warp_drive'; valid: .*device_offline"):
        validate_rule(AlertRule(id="r", name="r", kind="warp_drive"))
    for junk in ("abc", [1], {"a": 1}):
        with pytest.raises(ValueError, match="Must last for must be a number"):
            validate_rule(AlertRule(id="r", name="r", kind="device_offline", params={"for_s": junk}))
    with pytest.raises(ValueError, match="cooldown cannot be negative"):
        validate_rule(AlertRule(id="r", name="r", kind="device_offline", cooldown_s=-0.1))
    validate_rule(AlertRule(id="r", name="r", kind="device_offline", cooldown_s=0, params={"for_s": 0, "unrelated": "ignored"}))


_RANGES = [(kind, p.name, p.min, p.max) for kind, spec in RULE_SPECS.items() for p in spec.params
           if p.min is not None and p.max is not None]


@pytest.mark.parametrize(("kind", "param", "low", "high"), _RANGES, ids=[f"{k}.{p}" for k, p, _, _ in _RANGES])
def test_every_documented_parameter_range_is_enforced(kind, param, low, high):
    validate_rule(AlertRule(id="r", name="r", kind=kind, params={param: low}))
    validate_rule(AlertRule(id="r", name="r", kind=kind, params={param: high}))
    for bad in (low - 0.5, high + 0.5):
        with pytest.raises(ValueError, match="must be between"):
            validate_rule(AlertRule(id="r", name="r", kind=kind, params={param: bad}))


def test_the_rule_catalogue_is_consistent():
    state = {k for k, s in RULE_SPECS.items() if s.mode == "state"}
    events = {k for k, s in RULE_SPECS.items() if s.mode == "event"}
    assert state | events == set(RULE_SPECS) and not state & events
    assert state == set(EVALUATORS)  # every state rule has exactly one evaluator
    assert all(RULE_SPECS[k].event_type for k in events) and all(RULE_SPECS[k].event_type is None for k in state)
    for kind, spec in RULE_SPECS.items():
        assert spec.kind == kind and spec.label and spec.description and spec.scope in ("device", "fleet", "node")
        rule = AlertRule(id="r", name="r", kind=kind, params=spec.defaults(), cooldown_s=spec.cooldown_s)
        validate_rule(rule)  # the shipped defaults are inside their own limits
        as_dict = spec.as_dict()
        assert json.loads(json.dumps(as_dict)) == as_dict
        assert [p["name"] for p in as_dict["params"]] == [p.name for p in spec.params]
        if spec.mode == "state":
            assert any(p.name == "for_s" for p in spec.params)  # a state rule without a duration would flap


# --- evaluator boundaries (pure functions, no simulator) -----------------------------------------------------------------------------------


def fired(kind: str, devices: list[DeviceView], **kw: Any) -> bool:
    params = kw.pop("params", {})
    return bool(EVALUATORS[kind](rule_of(kind, **params), eval_ctx(devices, **kw)))


@pytest.mark.parametrize(
    ("telemetry", "fires"),
    [({"temp_asic_c": 75.0}, True), ({"temp_asic_c": 74.9}, False), ({"temp_vr_c": 90.0}, True), ({"temp_vr_c": 89.9}, False),
     ({}, False)],
)
def test_temp_high_limits_are_inclusive(telemetry, fires):
    assert fired("temp_high", [view(**telemetry)]) is fires


def test_temp_high_critical_line_is_inclusive_and_unknown_miners_are_skipped():
    [cond] = EVALUATORS["temp_high"](rule_of("temp_high"), eval_ctx([view(temp_asic_c=85.0)])).values()
    assert cond.severity == Severity.CRITICAL
    [cond] = EVALUATORS["temp_high"](rule_of("temp_high"), eval_ctx([view(temp_asic_c=84.9)])).values()
    assert cond.severity is None  # the rule's own severity applies
    assert not fired("temp_high", [view(status=DeviceStatus.UNKNOWN, temp_asic_c=99.0)])
    assert not fired("temp_high", [view(status=DeviceStatus.OFFLINE, temp_asic_c=99.0)])
    assert fired("temp_high", [view(status=DeviceStatus.PAUSED, temp_asic_c=99.0)])  # a paused chip can still be too hot


@pytest.mark.parametrize(
    ("telemetry", "fires"),
    [({"fan_rpm": 99, "fan_pct": 20, "temp_asic_c": 45}, True), ({"fan_rpm": 100, "fan_pct": 20, "temp_asic_c": 45}, False),
     ({"fan_rpm": 0, "fan_pct": 19.9, "temp_asic_c": 60}, False), ({"fan_rpm": 0, "fan_pct": 50, "temp_asic_c": 44.9}, False),
     ({"fan_rpm": None, "fan_pct": 50, "temp_asic_c": 60}, False), ({"fan_rpm": 0, "fan_pct": None, "temp_asic_c": 60}, False),
     ({"fan_rpm": 0, "fan_pct": 50, "temp_asic_c": None}, False)],
)
def test_fan_failure_boundaries(telemetry, fires):
    assert fired("fan_failure", [view(**telemetry)]) is fires


@pytest.mark.parametrize(
    ("accepted", "rejected", "fires"),
    [(190, 10, True), (191, 9, False), (189, 10, False), (950, 50, True)],  # (200 shares, 5 %) is the edge
)
def test_reject_rate_boundaries(accepted, rejected, fires):
    reject_rate_pct = rejected / (accepted + rejected) * 100
    d = view(shares_accepted=accepted, shares_rejected=rejected, reject_rate_pct=reject_rate_pct)
    assert fired("reject_rate_high", [d]) is fires


def test_reject_rate_skips_offline_miners_and_missing_percentages():
    assert not fired("reject_rate_high", [view(status=DeviceStatus.OFFLINE, shares_accepted=100, shares_rejected=900, reject_rate_pct=90.0)])
    assert not fired("reject_rate_high", [view(shares_accepted=100, shares_rejected=900, reject_rate_pct=None)])


@pytest.mark.parametrize(
    ("hashrate", "fires"),
    [(0.69e12, True), (0.71e12, False), (0.99e12, False), (0.0, True)],  # base 1 TH/s and a 30 % drop: below 0.7 TH/s fires
)
def test_hashrate_drop_threshold(hashrate, fires):
    d = view("d1", hashrate_hs=hashrate, uptime_s=5000)
    assert fired("hashrate_drop", [d], baselines={"d1": 1.0e12}) is fires


@pytest.mark.parametrize(("uptime", "fires"), [(899, False), (900, True), (None, True)])
def test_hashrate_drop_waits_900_seconds_after_a_reboot(uptime, fires):
    d = view("d1", hashrate_hs=0.1e12, uptime_s=uptime)
    assert fired("hashrate_drop", [d], baselines={"d1": 1.0e12}) is fires


def test_hashrate_drop_prefers_the_smoothed_reading():
    d = view("d1", hashrate_hs=0.1e12, uptime_s=5000).model_copy(update={"hashrate_smooth_hs": 0.95e12})
    assert not fired("hashrate_drop", [d], baselines={"d1": 1.0e12})  # one bad sample is not a drop
    d = view("d1", hashrate_hs=0.95e12, uptime_s=5000).model_copy(update={"hashrate_smooth_hs": 0.2e12})
    assert fired("hashrate_drop", [d], baselines={"d1": 1.0e12})


def test_rules_fall_back_to_the_spec_defaults_for_missing_params():
    rule = AlertRule(id="r", name="r", kind="temp_high", params={"asic_c": None})  # nothing usable stored
    assert EVALUATORS["temp_high"](rule, eval_ctx([view(temp_asic_c=75.0)]))
    assert not EVALUATORS["temp_high"](rule, eval_ctx([view(temp_asic_c=74.0)]))


def test_fleet_hashrate_drop_boundary():
    fleet = FleetSummary(hashrate_hs=0.75e12)
    assert not fired("fleet_hashrate_drop", [], summary=fleet, fleet_baseline=1.0e12)  # 25 % down is not *more* than 25 %
    assert fired("fleet_hashrate_drop", [], summary=FleetSummary(hashrate_hs=0.7499e12), fleet_baseline=1.0e12)
    assert not fired("fleet_hashrate_drop", [], summary=fleet, fleet_baseline=None)


def test_pool_fallback_ignores_offline_miners():
    on_fallback = {"using_fallback": True}
    assert fired("pool_fallback", [view(**on_fallback)])
    assert not fired("pool_fallback", [view(status=DeviceStatus.OFFLINE, **on_fallback)])
    assert not fired("pool_fallback", [view(using_fallback=False)])
    assert not fired("pool_fallback", [view(using_fallback=None)])
