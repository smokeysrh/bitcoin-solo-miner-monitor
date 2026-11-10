"""Issue #18: a rule whose evaluator fails must not be read as 'the problem cleared'.

An alert that is already firing keeps firing while its evaluator is broken; the "Resolved" message is sent
only after a *successful* evaluation has seen the condition absent for RESOLVE_AFTER_S. The engine is driven
tick by tick with a controllable clock and a capturing notification channel; the evaluator is the only fake.
"""

from __future__ import annotations

import time
from typing import Any

import pytest

import bsmm.engine.alerts as alerts_mod
from bsmm.engine.alerts import RESOLVE_AFTER_S, Condition
from bsmm.models import AlertRule, Channel
from bsmm.notify.channels import CHANNEL_CLASSES, BaseChannel, Notification

ALERT_KEY = "rule_device_offline:dev1"


class Evaluator:
    """Stands in for the device_offline evaluator; the test chooses what each tick sees."""

    def __init__(self) -> None:
        self.mode = "present"  # present | absent | broken

    def __call__(self, rule: AlertRule, ctx: Any) -> dict[str, Condition]:
        if self.mode == "broken":
            raise RuntimeError("evaluator failed on malformed input")
        if self.mode == "absent":
            return {}
        return {ALERT_KEY: Condition(ALERT_KEY, "Garage is offline", "No answer.", device_id="dev1")}


class Harness:
    def __init__(self, ctx: Any, evaluator: Evaluator) -> None:
        self.ctx = ctx
        self.evaluator = evaluator
        self.outbox: list[Notification] = []
        self.now = time.time()

    async def tick(self, mode: str, advance: float = 0.0) -> None:
        self.evaluator.mode = mode
        self.now += advance
        await self.ctx.alerts.tick(self.now)

    def resolved(self) -> list[Notification]:
        return [n for n in self.outbox if n.resolved]


@pytest.fixture
async def harness(lan, monkeypatch):
    ctx, _hosts = lan
    outbox: list[Notification] = []

    class Capture(BaseChannel):
        kind = "capture"
        label = "Capture"

        async def send(self, n: Notification) -> None:
            outbox.append(n)

    evaluator = Evaluator()
    monkeypatch.setitem(CHANNEL_CLASSES, "capture", Capture)
    monkeypatch.setattr(alerts_mod, "EVALUATORS", {"device_offline": evaluator})
    await ctx.store.save_channel(Channel(id="ch_main", kind="capture", name="Main", config={}))
    await ctx.alerts.ensure_default_rules()
    await ctx.alerts.update_rule("rule_device_offline", {"params": {"for_s": 0}})
    h = Harness(ctx, evaluator)
    h.outbox = outbox
    await h.tick("present")  # fires at once: for_s is 0
    assert [n.title for n in outbox] == ["Garage is offline"]
    return h


async def test_a_failing_evaluator_does_not_resolve_a_firing_alert(harness):
    h = harness
    for _ in range(4):  # far beyond the resolution period, and then some
        await h.tick("broken", RESOLVE_AFTER_S)
    assert h.resolved() == []
    assert [a["key"] for a in h.ctx.alerts.active_alerts()] == [ALERT_KEY]
    assert ALERT_KEY in await h.ctx.store.load_alert_state()


async def test_resolution_still_follows_a_successful_absence_after_a_failure(harness):
    h = harness
    await h.tick("broken", RESOLVE_AFTER_S * 2)
    assert h.resolved() == []
    await h.tick("absent", 1)  # a successful look starts the clearing timer
    assert h.resolved() == []
    await h.tick("absent", RESOLVE_AFTER_S)
    [n] = h.resolved()
    assert n.title == "Resolved: Garage is offline"
    assert h.ctx.alerts.active_alerts() == []
    assert await h.ctx.store.load_alert_state() == {}


async def test_a_failure_in_the_middle_of_clearing_restarts_the_timer(harness):
    h = harness
    await h.tick("absent", 1)
    await h.tick("broken", RESOLVE_AFTER_S - 1)
    await h.tick("absent", 2)  # more than RESOLVE_AFTER_S since the first absence, but one evaluation was blind
    assert h.resolved() == []
    await h.tick("absent", RESOLVE_AFTER_S)
    assert len(h.resolved()) == 1
