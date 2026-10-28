"""Alert rules: when to tell the user something, and the firing / resolved life-cycle.

Two kinds of rule:

* **state rules** watch a condition ("device offline", "too hot") and fire only after it has held for
  ``for_s`` seconds, remind at most every ``cooldown_s``, and send a "resolved" message when it clears;
* **event rules** turn a one-off event ("new best share", "block found") into a notification.

Rules are plain data (kind + parameters), never code, so they can be created from the UI, the API
or an AI agent without any risk of running arbitrary expressions.
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from bsmm.engine.bus import EventBus
from bsmm.engine.fleet import Fleet
from bsmm.engine.network import NetworkService
from bsmm.models import AlertRule, DeviceStatus, DeviceView, FleetSummary, Severity
from bsmm.notify.channels import Notification
from bsmm.notify.dispatcher import Notifier
from bsmm.settings import Settings, SettingsService
from bsmm.storage.store import Store, new_id
from bsmm.units import format_duration

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ParamSpec:
    name: str
    label: str
    type: str = "number"  # number | boolean | string
    default: Any = None
    min: float | None = None
    max: float | None = None
    unit: str = ""
    help: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


@dataclass(frozen=True, slots=True)
class RuleSpec:
    kind: str
    label: str
    description: str
    mode: str  # state | event
    severity: Severity
    enabled_by_default: bool
    params: tuple[ParamSpec, ...] = ()
    event_type: str | None = None
    cooldown_s: float = 3600.0
    scope: str = "device"  # device | fleet | node

    def defaults(self) -> dict[str, Any]:
        return {p.name: p.default for p in self.params}

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind, "label": self.label, "description": self.description, "mode": self.mode,
            "severity": self.severity.value, "enabled_by_default": self.enabled_by_default, "scope": self.scope,
            "cooldown_s": self.cooldown_s, "params": [p.as_dict() for p in self.params],
        }


FOR = ParamSpec("for_s", "Must last for", "number", 120, 0, 86400, "s", "How long the problem has to persist before you are told.")

RULE_SPECS: dict[str, RuleSpec] = {s.kind: s for s in (
    RuleSpec("device_offline", "A miner goes offline", "A miner stops answering.", "state", Severity.CRITICAL, True,
             (ParamSpec("for_s", "Must last for", "number", 120, 0, 86400, "s"),), cooldown_s=3 * 3600),
    RuleSpec("temp_high", "A miner runs hot", "ASIC or voltage-regulator temperature is above your limit.", "state", Severity.WARNING, True,
             (ParamSpec("asic_c", "ASIC limit", "number", 75, 40, 120, "°C"), ParamSpec("vr_c", "Regulator limit", "number", 90, 40, 130, "°C"),
              ParamSpec("for_s", "Must last for", "number", 60, 0, 3600, "s")), cooldown_s=1800),
    RuleSpec("fan_failure", "A fan stops", "The fan reports 0 rpm although it is being asked to spin and the chip is warm.", "state",
             Severity.CRITICAL, True, (ParamSpec("for_s", "Must last for", "number", 60, 0, 3600, "s"),), cooldown_s=3600),
    RuleSpec("hashrate_drop", "Hashrate drops", "A miner is hashing much less than it usually does.", "state", Severity.WARNING, True,
             (ParamSpec("drop_pct", "Drop of at least", "number", 30, 5, 95, "%"), ParamSpec("for_s", "Must last for", "number", 600, 0, 86400, "s")),
             cooldown_s=3 * 3600),
    RuleSpec("fleet_hashrate_drop", "Total hashrate drops", "The whole fleet is hashing much less than usual.", "state", Severity.WARNING, False,
             (ParamSpec("drop_pct", "Drop of at least", "number", 25, 5, 95, "%"), ParamSpec("for_s", "Must last for", "number", 600, 0, 86400, "s")),
             cooldown_s=3 * 3600, scope="fleet"),
    RuleSpec("reject_rate_high", "Many rejected shares", "Too many of a miner's shares are rejected (usually a network or pool problem).", "state",
             Severity.WARNING, True, (ParamSpec("pct", "Reject rate above", "number", 5, 0.5, 50, "%"),
                                      ParamSpec("min_shares", "After at least", "number", 200, 10, 1_000_000, "shares"),
                                      ParamSpec("for_s", "Must last for", "number", 600, 0, 86400, "s")), cooldown_s=6 * 3600),
    RuleSpec("pool_fallback", "A miner uses its fallback pool", "It is no longer mining to your primary pool or node.", "state",
             Severity.WARNING, True, (ParamSpec("for_s", "Must last for", "number", 120, 0, 86400, "s"),), cooldown_s=6 * 3600),
    RuleSpec("device_attention", "A miner needs attention", "Any other problem the app detects (not hashing, pool disconnected, fault).", "state",
             Severity.WARNING, False, (ParamSpec("for_s", "Must last for", "number", 180, 0, 86400, "s"),), cooldown_s=3 * 3600),
    RuleSpec("node_down", "Node or pool unreachable", "A Bitcoin node or pool you configured stops answering.", "state", Severity.WARNING, True,
             (ParamSpec("for_s", "Must last for", "number", 180, 0, 86400, "s"),), cooldown_s=3 * 3600, scope="node"),
    RuleSpec("node_behind", "Node is behind the network", "Your node has fallen behind the chain tip.", "state", Severity.WARNING, True,
             (ParamSpec("blocks", "Behind by more than", "number", 3, 1, 1000, "blocks"), ParamSpec("for_s", "Must last for", "number", 600, 0, 86400, "s")),
             cooldown_s=6 * 3600, scope="node"),
    RuleSpec("new_best_share", "New best share", "A miner beats its own best share difficulty.", "event", Severity.SUCCESS, True,
             event_type="new_best_share", cooldown_s=300),
    RuleSpec("block_found", "BLOCK FOUND", "You found a Bitcoin block.", "event", Severity.SUCCESS, True, event_type="block_found", cooldown_s=0),
    RuleSpec("device_restarted", "A miner restarts", "A miner rebooted (uptime reset).", "event", Severity.INFO, False,
             event_type="device_restarted", cooldown_s=600),
    RuleSpec("difficulty_adjusted", "Difficulty adjusts", "The network difficulty changed.", "event", Severity.INFO, False,
             event_type="difficulty_adjusted", cooldown_s=0),
    RuleSpec("firmware_changed", "Firmware changes", "A miner is running different firmware than before.", "event", Severity.INFO, False,
             event_type="firmware_changed", cooldown_s=0),
)}


@dataclass(slots=True)
class Condition:
    key: str
    title: str
    body: str = ""
    device_id: str | None = None
    severity: Severity | None = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvalContext:
    now: float
    devices: list[DeviceView]
    summary: FleetSummary
    network: Any  # NetworkState
    settings: Settings
    baselines: dict[str, float]
    fleet_baseline: float | None


def in_scope(rule: AlertRule, d: DeviceView) -> bool:
    scope = rule.scope or {"all": True}
    if scope.get("all", False) and not scope.get("device_ids") and not scope.get("tags"):
        return True
    if d.id in (scope.get("device_ids") or []):
        return True
    return bool(set(scope.get("tags") or []) & set(d.tags))


def _p(rule: AlertRule, name: str) -> Any:
    spec = RULE_SPECS[rule.kind]
    if name in rule.params and rule.params[name] is not None:
        return rule.params[name]
    return spec.defaults().get(name)


# --- evaluators (one per state rule) ---------------------------------------------------------------------------


def _ago(ctx: EvalContext, ts: float | None) -> str:
    return format_duration(ctx.now - ts) if ts else "an unknown time"


def eval_device_offline(rule: AlertRule, ctx: EvalContext) -> dict[str, Condition]:
    out: dict[str, Condition] = {}
    for d in ctx.devices:
        if in_scope(rule, d) and d.status == DeviceStatus.OFFLINE:
            out[f"{rule.id}:{d.id}"] = Condition(
                f"{rule.id}:{d.id}", f"{d.name} is offline",
                f"No answer from {d.host} for {_ago(ctx, d.status_since)}. Last error: {d.last_error or 'none'}.", d.id)
    return out


def eval_temp_high(rule: AlertRule, ctx: EvalContext) -> dict[str, Condition]:
    asic_lim, vr_lim = float(_p(rule, "asic_c")), float(_p(rule, "vr_c"))
    out: dict[str, Condition] = {}
    for d in ctx.devices:
        t = d.telemetry
        if not t or d.status in (DeviceStatus.OFFLINE, DeviceStatus.UNKNOWN) or not in_scope(rule, d):
            continue
        hot = []
        if t.temp_asic_c is not None and t.temp_asic_c >= asic_lim:
            hot.append(f"ASIC {t.temp_asic_c:.0f} °C (limit {asic_lim:.0f})")
        if t.temp_vr_c is not None and t.temp_vr_c >= vr_lim:
            hot.append(f"voltage regulator {t.temp_vr_c:.0f} °C (limit {vr_lim:.0f})")
        if hot:
            sev = Severity.CRITICAL if (t.temp_asic_c or 0) >= ctx.settings.alerts.temp_crit_c else None
            out[f"{rule.id}:{d.id}"] = Condition(f"{rule.id}:{d.id}", f"{d.name} is running hot", "; ".join(hot) + ". Check airflow and the fan.", d.id, sev)
    return out


def eval_fan_failure(rule: AlertRule, ctx: EvalContext) -> dict[str, Condition]:
    out: dict[str, Condition] = {}
    for d in ctx.devices:
        t = d.telemetry
        if not t or d.status in (DeviceStatus.OFFLINE, DeviceStatus.UNKNOWN, DeviceStatus.PAUSED) or not in_scope(rule, d):
            continue
        if t.fan_rpm is not None and t.fan_rpm < 100 and (t.fan_pct or 0) >= 20 and (t.temp_asic_c or 0) >= 45:
            out[f"{rule.id}:{d.id}"] = Condition(
                f"{rule.id}:{d.id}", f"{d.name}: the fan is not spinning",
                f"The fan is set to {t.fan_pct:.0f}% but reads {t.fan_rpm:.0f} rpm while the chip is at {t.temp_asic_c:.0f} °C. Stop the miner if this continues.", d.id)
    return out


def eval_hashrate_drop(rule: AlertRule, ctx: EvalContext) -> dict[str, Condition]:
    drop = float(_p(rule, "drop_pct")) / 100.0
    out: dict[str, Condition] = {}
    for d in ctx.devices:
        base = ctx.baselines.get(d.id)
        t = d.telemetry
        if not base or not t or d.status in (DeviceStatus.OFFLINE, DeviceStatus.UNKNOWN, DeviceStatus.PAUSED) or not in_scope(rule, d):
            continue
        if (t.uptime_s or 10**9) < 900:  # a freshly rebooted miner is still ramping up
            continue
        now_hr = d.hashrate_smooth_hs if d.hashrate_smooth_hs is not None else (t.hashrate_hs or 0.0)
        if now_hr < base * (1 - drop):
            out[f"{rule.id}:{d.id}"] = Condition(
                f"{rule.id}:{d.id}", f"{d.name}: hashrate is down {100 * (1 - now_hr / base):.0f}%",
                f"It is doing {now_hr / 1e12:.2f} TH/s; it normally does about {base / 1e12:.2f} TH/s.", d.id)
    return out


def eval_fleet_hashrate_drop(rule: AlertRule, ctx: EvalContext) -> dict[str, Condition]:
    base = ctx.fleet_baseline
    if not base:
        return {}
    drop = float(_p(rule, "drop_pct")) / 100.0
    now_hr = ctx.summary.hashrate_hs
    if now_hr < base * (1 - drop):
        return {f"{rule.id}:fleet": Condition(
            f"{rule.id}:fleet", f"Total hashrate is down {100 * (1 - now_hr / base):.0f}%",
            f"The fleet is at {now_hr / 1e12:.2f} TH/s; it normally does about {base / 1e12:.2f} TH/s.")}
    return {}


def eval_reject_rate(rule: AlertRule, ctx: EvalContext) -> dict[str, Condition]:
    lim, min_shares = float(_p(rule, "pct")), int(_p(rule, "min_shares"))
    out: dict[str, Condition] = {}
    for d in ctx.devices:
        t = d.telemetry
        if not t or d.status == DeviceStatus.OFFLINE or not in_scope(rule, d):
            continue
        total = (t.shares_accepted or 0) + (t.shares_rejected or 0)
        if total >= min_shares and t.reject_rate_pct is not None and t.reject_rate_pct >= lim:
            reasons = ""
            if t.rejected_reasons:
                top = max(t.rejected_reasons.items(), key=lambda kv: kv[1])
                reasons = f" Most common reason: {top[0]} ({top[1]})."
            out[f"{rule.id}:{d.id}"] = Condition(
                f"{rule.id}:{d.id}", f"{d.name}: {t.reject_rate_pct:.1f}% of shares are rejected",
                f"{t.shares_rejected} of {total} shares were rejected.{reasons} A weak WiFi signal is the usual cause.", d.id)
    return out


def eval_pool_fallback(rule: AlertRule, ctx: EvalContext) -> dict[str, Condition]:
    out: dict[str, Condition] = {}
    for d in ctx.devices:
        t = d.telemetry
        if t and t.using_fallback and d.status != DeviceStatus.OFFLINE and in_scope(rule, d):
            ap = t.active_pool()
            out[f"{rule.id}:{d.id}"] = Condition(
                f"{rule.id}:{d.id}", f"{d.name} is using its fallback pool",
                f"It switched to {ap.endpoint if ap else 'the fallback'}, so it is not mining to your primary pool/node right now.", d.id)
    return out


def eval_device_attention(rule: AlertRule, ctx: EvalContext) -> dict[str, Condition]:
    out: dict[str, Condition] = {}
    for d in ctx.devices:
        if d.status == DeviceStatus.DEGRADED and in_scope(rule, d) and d.status_reason != "Restarting":
            out[f"{rule.id}:{d.id}"] = Condition(f"{rule.id}:{d.id}", f"{d.name} needs attention", d.status_reason or "", d.id)
    return out


def eval_node_down(rule: AlertRule, ctx: EvalContext) -> dict[str, Condition]:
    out: dict[str, Condition] = {}
    for s in ctx.network.sources:
        if s.ok is False and s.kind in ("bitcoin_core", "public_pool", "ckpool") and not s.implicit:
            out[f"{rule.id}:{s.id}"] = Condition(f"{rule.id}:{s.id}", f"Can't reach {s.name}", s.error or "No answer.")
    return out


def eval_node_behind(rule: AlertRule, ctx: EvalContext) -> dict[str, Condition]:
    behind = ctx.network.node_behind_by
    if behind is not None and behind > int(_p(rule, "blocks")):
        return {f"{rule.id}:node": Condition(
            f"{rule.id}:node", f"Your node is {behind} blocks behind",
            "It may be syncing or have lost its peers. Mining against a stale node wastes hashes.")}
    return {}


EVALUATORS: dict[str, Callable[[AlertRule, EvalContext], dict[str, Condition]]] = {
    "device_offline": eval_device_offline, "temp_high": eval_temp_high, "fan_failure": eval_fan_failure,
    "hashrate_drop": eval_hashrate_drop, "fleet_hashrate_drop": eval_fleet_hashrate_drop, "reject_rate_high": eval_reject_rate,
    "pool_fallback": eval_pool_fallback, "device_attention": eval_device_attention, "node_down": eval_node_down,
    "node_behind": eval_node_behind,
}

RESOLVE_AFTER_S = 30.0
EVENT_BATCH_SIZE = 128
EVENT_REPLAY_POLL_S = 2.0


@dataclass(slots=True)
class _Track:
    rule_id: str
    first_seen: float
    firing: bool = False
    since: float = 0.0
    last_notified: float | None = None
    clear_since: float | None = None
    cond: Condition | None = None


def validate_rule(rule: AlertRule) -> None:
    spec = RULE_SPECS.get(rule.kind)
    if spec is None:
        raise ValueError(f"unknown rule type {rule.kind!r}; valid: {', '.join(sorted(RULE_SPECS))}")
    for p in spec.params:
        if p.name in rule.params and rule.params[p.name] is not None:
            try:
                v = float(rule.params[p.name])
            except (TypeError, ValueError) as e:
                raise ValueError(f"{p.label} must be a number") from e
            if not math.isfinite(v):
                raise ValueError(f"{p.label} must be finite")
            if (p.min is not None and v < p.min) or (p.max is not None and v > p.max):
                raise ValueError(f"{p.label} must be between {p.min} and {p.max}")
            rule.params[p.name] = v
    try:
        cooldown = float(rule.cooldown_s)
    except (TypeError, ValueError) as e:
        raise ValueError("cooldown must be a finite nonnegative number") from e
    if not math.isfinite(cooldown):
        raise ValueError("cooldown must be a finite nonnegative number")
    if cooldown < 0:
        raise ValueError("cooldown cannot be negative")
    rule.cooldown_s = cooldown


class AlertEngine:
    def __init__(self, store: Store, settings: SettingsService, bus: EventBus, fleet: Fleet, network: NetworkService, notifier: Notifier) -> None:
        self.store = store
        self.settings = settings
        self.bus = bus
        self.fleet = fleet
        self.network = network
        self.notifier = notifier
        self._tracks: dict[str, _Track] = {}
        self._baselines: dict[str, float] = {}
        self._fleet_baseline: float | None = None
        self._baseline_at = 0.0
        self._tasks: list[asyncio.Task[None]] = []
        self._running = False
        self._event_last: dict[str, float] = {}

    async def start(self) -> None:
        await self.ensure_default_rules()
        for key, row in (await self.store.load_alert_state()).items():
            data = row.get("data") or {}
            cond = None
            if data.get("title"):
                try:
                    sev = Severity(data["severity"]) if data.get("severity") else None
                except ValueError:
                    sev = None
                cond = Condition(key, str(data["title"]), str(data.get("body") or ""), row.get("device_id"), sev)
            self._tracks[key] = _Track(row["rule_id"], row["since"], True, row["since"], row["last_notified"], cond=cond)
        self._running = True
        self._tasks = [asyncio.create_task(self._tick_loop(), name="alert-ticks"), asyncio.create_task(self._event_loop(), name="alert-events")]

    async def stop(self) -> None:
        self._running = False
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def ensure_default_rules(self) -> None:
        existing = {r.kind for r in await self.store.list_rules() if r.builtin}
        for spec in RULE_SPECS.values():
            if spec.kind in existing:
                continue
            await self.store.save_rule(AlertRule(
                id=f"rule_{spec.kind}", name=spec.label, kind=spec.kind, enabled=spec.enabled_by_default, severity=spec.severity,
                params=spec.defaults(), cooldown_s=spec.cooldown_s, builtin=True))

    async def create_rule(self, data: dict[str, Any]) -> AlertRule:
        spec = RULE_SPECS.get(str(data.get("kind")))
        if spec is None:
            raise ValueError(f"unknown rule type {data.get('kind')!r}")
        rule = AlertRule(
            id=new_id("rule"), name=data.get("name") or spec.label, kind=spec.kind, enabled=bool(data.get("enabled", True)),
            severity=Severity(data.get("severity", spec.severity.value)), scope=data.get("scope") or {"all": True},
            params={**spec.defaults(), **(data.get("params") or {})}, channel_ids=list(data.get("channel_ids") or []),
            cooldown_s=float(data.get("cooldown_s", spec.cooldown_s)))
        validate_rule(rule)
        await self.store.save_rule(rule)
        return rule

    async def update_rule(self, rule_id: str, patch: dict[str, Any]) -> AlertRule:
        rule = await self.store.get_rule(rule_id)
        if rule is None:
            raise KeyError(rule_id)
        for key in ("name", "enabled", "scope", "channel_ids", "cooldown_s"):
            if key in patch:
                setattr(rule, key, patch[key])
        if "severity" in patch:
            rule.severity = Severity(patch["severity"])
        if "params" in patch:
            rule.params = {**rule.params, **patch["params"]}
        validate_rule(rule)
        await self.store.save_rule(rule)
        if not rule.enabled:
            await self._clear_rule(rule_id)
        return rule

    async def _clear_rule(self, rule_id: str) -> None:
        for key in [k for k, t in self._tracks.items() if t.rule_id == rule_id]:
            self._tracks.pop(key, None)
            await self.store.clear_alert_state(key)

    # -- baselines -------------------------------------------------------------------------------------------

    async def refresh_baselines(self, now: float) -> None:
        self._baseline_at = now
        try:
            hist = await self.store.samples.history(metrics=["hashrate_hs"], start=now - 6 * 3600, end=now - 600, step=300, per_device=True)
        except ValueError:
            return
        fleet_series: dict[int, float] = {}
        for dev_id, series in hist.devices.items():
            vals = sorted(v for v in series["hashrate_hs"] if v)
            if len(vals) >= 6:
                self._baselines[dev_id] = vals[len(vals) // 2]  # median resists past outages
            for t, v in zip(hist.t, series["hashrate_hs"], strict=True):
                if v:
                    fleet_series[t] = fleet_series.get(t, 0.0) + v
        fv = sorted(fleet_series.values())
        if len(fv) >= 6:  # too little history must not erase a baseline we already learned
            self._fleet_baseline = fv[len(fv) // 2]

    def active_alerts(self) -> list[dict[str, Any]]:
        out = []
        for key, tr in self._tracks.items():
            if tr.firing and tr.cond:
                out.append({"key": key, "rule_id": tr.rule_id, "since": tr.since, "title": tr.cond.title, "body": tr.cond.body,
                            "device_id": tr.cond.device_id, "severity": (tr.cond.severity or Severity.WARNING).value})
        return sorted(out, key=lambda a: a["since"])

    # -- ticking -----------------------------------------------------------------------------------------------

    async def _tick_loop(self) -> None:
        while self._running:
            try:
                await self.tick(time.time())
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("alert evaluation failed")
            await asyncio.sleep(10)

    async def tick(self, now: float) -> None:
        if now - self._baseline_at > 300:
            await self.refresh_baselines(now)
        ctx = EvalContext(now=now, devices=self.fleet.views(), summary=self.fleet.summary(fresh=True), network=self.network.state,
                          settings=self.settings.current, baselines=self._baselines, fleet_baseline=self._fleet_baseline)
        rules = [r for r in await self.store.list_rules() if r.enabled and r.kind in EVALUATORS]
        active: dict[str, tuple[AlertRule, Condition]] = {}
        for rule in rules:
            try:
                for key, cond in EVALUATORS[rule.kind](rule, ctx).items():
                    active[key] = (rule, cond)
            except Exception:
                log.exception("rule %s failed", rule.name)
        rules_by_id = {r.id: r for r in rules}
        for key, (rule, cond) in active.items():
            tr = self._tracks.get(key)
            if tr is None:
                tr = self._tracks[key] = _Track(rule.id, now)
            if cond.severity is None:  # the rule's own severity applies; keep it on the condition so active_alerts() agrees with the notification
                cond.severity = rule.severity
            tr.cond = cond
            tr.clear_since = None
            for_s = float(rule.params.get("for_s") or 0)
            if not tr.firing and now - tr.first_seen >= for_s:
                tr.firing, tr.since = True, now
                await self._notify(rule, cond, resolved=False, tr=tr, now=now)
            elif tr.firing and rule.cooldown_s > 0 and tr.last_notified and now - tr.last_notified >= rule.cooldown_s:
                await self._notify(rule, cond, resolved=False, tr=tr, now=now, reminder=True)
        for key in list(self._tracks):
            if key in active:
                continue
            tr = self._tracks[key]
            owner = rules_by_id.get(tr.rule_id)
            if owner is None:  # rule disabled or deleted
                self._tracks.pop(key, None)
                await self.store.clear_alert_state(key)
                continue
            if not tr.firing:
                self._tracks.pop(key, None)
                continue
            tr.clear_since = tr.clear_since or now
            if now - tr.clear_since >= RESOLVE_AFTER_S:
                if tr.cond:
                    await self._notify(owner, tr.cond, resolved=True, tr=tr, now=now)
                self._tracks.pop(key, None)
                await self.store.clear_alert_state(key)
        self.bus.publish("alerts", {"active": self.active_alerts()})

    async def _notify(self, rule: AlertRule, cond: Condition, *, resolved: bool, tr: _Track, now: float, reminder: bool = False) -> None:
        if resolved:
            n = Notification(title=f"Resolved: {cond.title}", body=f"This problem cleared after {format_duration(now - tr.since)}.",
                             severity=Severity.SUCCESS, type=rule.kind, device_id=cond.device_id, resolved=True)
        else:
            title = f"Still a problem: {cond.title}" if reminder else cond.title
            n = Notification(title=title, body=cond.body, severity=cond.severity or rule.severity, type=rule.kind,
                             device_id=cond.device_id, data={"rule_id": rule.id, **cond.data})
            tr.last_notified = now
            # keep enough to describe the alert after a restart, so it can still be shown and later "Resolved"
            saved = {"title": cond.title, "body": cond.body, "severity": (cond.severity or rule.severity).value}
            await self.store.save_alert_state(cond.key, rule.id, cond.device_id, tr.since, now, saved)
        await self.notifier.dispatch(n, rule.channel_ids or None)

    # -- event rules --------------------------------------------------------------------------------------------------

    async def prepare_event_cursor(self) -> int:
        """Establish the first durable baseline before event producers start."""
        async with self.store.db.tx():
            cursor = await self.store.kv_get("alerts.event_cursor")
            if cursor is None:
                cursor = int(await self.store.db.scalar("SELECT COALESCE(MAX(id), 0) FROM events"))
                await self.store.kv_set("alerts.event_cursor", cursor)
        return int(cursor)

    async def _event_loop(self) -> None:
        # The bus is only a wakeup. Replay the existing durable event log in bounded
        # batches, so a slow notification transport cannot drop a one-shot event.
        cursor = await self.prepare_event_cursor()
        sub = self.bus.subscribe({"event"})
        try:
            while True:
                try:
                    events = await self.store.events_after(int(cursor), limit=EVENT_BATCH_SIZE)
                    if events and events[0].id is not None and events[0].id > int(cursor) + 1:
                        log.error("Alert replay gap after event %s: next retained event is %s (check event retention)", cursor, events[0].id)
                    for ev in events:
                        assert ev.id is not None  # events_after returns persisted events
                        await self.handle_event(ev.model_dump(mode="json"))
                        await self.store.kv_set("alerts.event_cursor", ev.id)
                        cursor = ev.id
                    if events:
                        continue
                    msg = await sub.get(EVENT_REPLAY_POLL_S)
                    if msg is not None and msg.data.get("id") is None:
                        await self.handle_event(msg.data)  # ephemeral callers; durable events use replay
                except Exception:
                    log.exception("event rule handling failed; persisted cursor retained for retry")
                    await asyncio.sleep(EVENT_REPLAY_POLL_S)
        finally:
            sub.close()

    async def handle_event(self, ev: dict[str, Any]) -> None:
        etype = ev.get("type")
        for rule in await self.store.list_rules():
            spec = RULE_SPECS.get(rule.kind)
            if not rule.enabled or spec is None or spec.mode != "event" or spec.event_type != etype:
                continue
            scope = rule.scope or {"all": True}
            if scope.get("device_ids") or scope.get("tags") or not scope.get("all", False):
                device = next((d for d in self.fleet.views() if d.id == ev.get("device_id")), None)
                # Global/address-only events cannot satisfy a device scope.
                if device is None or not in_scope(rule, device):
                    continue
            key = f"{rule.id}:{ev.get('device_id') or 'x'}"
            now = time.time()
            saved = await self.store.kv_get(f"alerts.event_rule:{key}", {})
            event_id = ev.get("id")
            if event_id is not None and event_id <= saved.get("event_id", 0):
                continue
            last = max(self._event_last.get(key, 0.0), saved.get("last_notified", 0.0))
            if rule.cooldown_s > 0 and now - last < rule.cooldown_s:
                continue
            sev = rule.severity
            n = Notification(title=str(ev.get("title", rule.name)), body=str(ev.get("body") or ""), severity=sev, type=rule.kind,
                             device_id=ev.get("device_id"), data=ev.get("data") or {})
            await self.notifier.dispatch(n, rule.channel_ids or None)
            # A dispatch attempt is acknowledged only after it completes. Provider failures
            # are recorded by Notifier; cancellation before this point is replayable.
            await self.store.kv_set(f"alerts.event_rule:{key}", {"event_id": event_id or 0, "last_notified": now})
            self._event_last[key] = now
