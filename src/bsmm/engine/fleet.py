"""The fleet engine: owns every monitored miner, polls them, tracks their state, raises events.

One asyncio task per device (jittered so a hundred miners are not all hit in the same second), a
shared concurrency limit, back-off for devices that stop answering, and batched sample writes.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import math
import random
import sqlite3
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

import httpx

from bsmm import mining
from bsmm.bitcoin_address import parse_address
from bsmm.drivers.base import ActionFailed, Driver, DriverError, IdentityMismatch, Unsupported, check_identity
from bsmm.drivers.registry import driver_for, probe_host
from bsmm.engine.bus import EventBus
from bsmm.engine.events import EventLog
from bsmm.models import (
    Capability,
    Device,
    DeviceStatus,
    DeviceView,
    FleetSummary,
    PoolUsage,
    ProbeResult,
    Severity,
    Telemetry,
    compute_efficiency,
    compute_reject_rate,
)
from bsmm.settings import Settings, SettingsService
from bsmm.storage.samples import telemetry_to_row
from bsmm.storage.store import Store

log = logging.getLogger(__name__)

SMOOTHING_TAU_S = 45.0
SPARK_POINTS = 30
RESTART_GRACE_S = 150.0

_T = TypeVar("_T")


async def _complete(task: asyncio.Task[_T]) -> _T:
    """Finish owned persistence before releasing locks, even if the caller is cancelled."""
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
    result = task.result()
    if cancelled:
        raise asyncio.CancelledError
    return result


@dataclass(slots=True)
class DeviceRuntime:
    device: Device
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    removing: bool = False
    driver: Driver | None = None
    status: DeviceStatus = DeviceStatus.UNKNOWN
    status_since: float = field(default_factory=time.time)
    status_reason: str | None = None
    failures: int = 0
    last_error: str | None = None
    telemetry: Telemetry | None = None
    hashrate_smooth: float | None = None
    last_ok_ts: float | None = None
    last_poll_ms: float | None = None
    task: asyncio.Task[None] | None = None
    wake: asyncio.Event = field(default_factory=asyncio.Event)
    expect_back_until: float = 0.0
    spark: deque[float | None] = field(default_factory=lambda: deque(maxlen=SPARK_POINTS * 3))
    last_seen_dirty: bool = False
    offline_since: float | None = None


@dataclass(slots=True)
class AddResult:
    device: Device
    created: bool
    merged: bool = False
    note: str | None = None


def derive_status(t: Telemetry, settings: Settings) -> tuple[DeviceStatus, str | None]:
    """Is a device that answered actually healthy? Only objective problems count as 'degraded'."""
    if t.mining_paused:
        return DeviceStatus.PAUSED, "Mining is paused on the device"
    reasons: list[str] = []
    if t.fault:
        reasons.append(f"Fault reported: {t.fault}")
    if t.pool_connected is False:
        reasons.append("Not connected to its pool")
    if t.using_fallback:
        reasons.append("Mining on the fallback pool")
    if t.hashrate_hs is not None and t.hashrate_hs <= 0 and (t.uptime_s is None or t.uptime_s > 120):
        reasons.append("Not hashing")
    crit = settings.alerts.temp_crit_c
    if t.temp_asic_c is not None and t.temp_asic_c >= crit:
        reasons.append(f"ASIC temperature {t.temp_asic_c:.0f} C")
    if t.temp_vr_c is not None and t.temp_vr_c >= settings.alerts.vr_temp_warn_c + 10:
        reasons.append(f"Voltage regulator at {t.temp_vr_c:.0f} C")
    if reasons:
        return DeviceStatus.DEGRADED, "; ".join(reasons)
    return DeviceStatus.ONLINE, None


def build_summary(runtimes: list[DeviceRuntime], settings: Settings, *, demo: bool = False) -> FleetSummary:
    s = FleetSummary(updated_at=time.time(), devices_total=len(runtimes), demo=demo)
    temps: list[float] = []
    pools: dict[tuple[str, bool], int] = {}
    addresses: list[str] = []
    expected = 0.0
    have_expected = False
    expected_actual = 0.0  # hashrate of just the miners that report an expectation (like for like)
    best = 0.0
    power = 0.0
    have_power = False
    eff_hash = 0.0
    eff_power = 0.0
    for rt in runtimes:
        match rt.status:
            case DeviceStatus.ONLINE:
                s.devices_online += 1
            case DeviceStatus.DEGRADED:
                s.devices_degraded += 1
            case DeviceStatus.OFFLINE:
                s.devices_offline += 1
            case DeviceStatus.PAUSED:
                s.devices_paused += 1
        t = rt.telemetry
        if t is None or rt.status in (DeviceStatus.OFFLINE, DeviceStatus.UNKNOWN, DeviceStatus.DISABLED):
            continue
        hr_s = rt.hashrate_smooth if rt.hashrate_smooth is not None else (t.hashrate_hs or 0.0)
        s.hashrate_hs += hr_s
        s.hashrate_raw_hs += t.hashrate_hs or 0.0
        if t.hashrate_expected_hs:
            expected += t.hashrate_expected_hs
            expected_actual += hr_s
            have_expected = True
        if t.power_w:
            power += t.power_w
            have_power = True
            if hr_s > 0:
                eff_power += t.power_w
                eff_hash += hr_s
        if t.temp_asic_c is not None:
            temps.append(t.temp_asic_c)
        s.shares_accepted += t.shares_accepted or 0
        s.shares_rejected += t.shares_rejected or 0
        if t.best_diff and t.best_diff > best:
            best = t.best_diff
            s.best_diff_device_id = rt.device.id
        if t.best_session_diff and (s.best_session_diff is None or t.best_session_diff > s.best_session_diff):
            s.best_session_diff = t.best_session_diff
        s.blocks_found_by_devices += t.blocks_found or 0
        active = t.active_pool()
        if active and active.endpoint:
            key = (active.endpoint, bool(t.using_fallback))
            pools[key] = pools.get(key, 0) + 1
        for p in t.pools:
            if p.address and p.address not in addresses:
                addresses.append(p.address)
    s.best_diff = best or None
    s.expected_hashrate_hs = expected if have_expected else None
    if have_expected and expected > 0:
        s.performance_pct = expected_actual / expected * 100.0
    if have_power:
        s.power_w = power
        s.power_wall_w = power * (1 + settings.energy.psu_overhead_pct / 100.0)
    if eff_hash > 0:
        s.efficiency_j_th = eff_power / (eff_hash / 1e12)
    if temps:
        s.temp_avg_c = sum(temps) / len(temps)
        s.temp_max_c = max(temps)
    s.reject_rate_pct = compute_reject_rate(s.shares_accepted, s.shares_rejected)
    s.pools = sorted((PoolUsage(endpoint=e, devices=n, is_fallback=fb) for (e, fb), n in pools.items()), key=lambda p: -p.devices)
    s.addresses = addresses
    return s


class Fleet:
    def __init__(
        self,
        store: Store,
        settings: SettingsService,
        bus: EventBus,
        events: EventLog,
        http: httpx.AsyncClient,
        *,
        demo: bool = False,
    ) -> None:
        self.store = store
        self.settings = settings
        self.bus = bus
        self.events = events
        self.http = http
        self.demo = demo
        self.runtimes: dict[str, DeviceRuntime] = {}
        self._sem = asyncio.Semaphore(settings.current.polling.concurrency)
        self._pending: list[dict[str, Any]] = []
        self._sample_lock = asyncio.Lock()
        self._bg: list[asyncio.Task[None]] = []
        self._running = False
        self._stopping = False
        #: set by the app so luck accounting knows the current network difficulty
        self.difficulty_provider: Callable[[], float | None] = lambda: None
        self._work_dirty = False
        self._work_hashes = 0.0
        self._work_blocks = 0.0
        self._summary_cache: FleetSummary | None = None

    # -- lifecycle ----------------------------------------------------------------------------------

    async def start(self) -> None:
        self._stopping = False
        self._running = True
        self._work_hashes = float(await self.store.kv_get("luck.total_hashes", 0.0))
        self._work_blocks = float(await self.store.kv_get("luck.expected_blocks", 0.0))
        if await self.store.kv_get("luck.since") is None:
            await self.store.kv_set("luck.since", time.time())
        for dev in await self.store.list_devices():
            self._spawn(dev)
        self._bg = [
            asyncio.create_task(self._writer_loop(), name="sample-writer"),
            asyncio.create_task(self._housekeeping_loop(), name="fleet-housekeeping"),
            asyncio.create_task(self._summary_loop(), name="fleet-summary"),
        ]
        self.settings.on_change(self._on_settings_change)

    async def stop(self) -> None:
        self._stopping = True
        await _complete(asyncio.create_task(self._stop()))

    async def _stop(self) -> None:
        self._running = False
        for rt in self.runtimes.values():
            if rt.task:
                rt.task.cancel()
        for t in self._bg:
            t.cancel()
        await asyncio.gather(*[rt.task for rt in self.runtimes.values() if rt.task], *self._bg, return_exceptions=True)
        # Also drain explicit poll/control calls, not just background poll tasks.
        for rt in list(self.runtimes.values()):
            async with rt.lock:
                pass
        await self._flush_samples()
        await self._flush_misc(force=True)
        for rt in list(self.runtimes.values()):
            if rt.driver:
                with contextlib.suppress(Exception):
                    await rt.driver.close()

    def _on_settings_change(self, new: Settings, old: Settings) -> None:
        if new.polling.concurrency != old.polling.concurrency:
            self._sem = asyncio.Semaphore(new.polling.concurrency)
        for rt in self.runtimes.values():
            rt.wake.set()

    # -- device management -------------------------------------------------------------------------------

    def _spawn(self, dev: Device) -> DeviceRuntime:
        rt = DeviceRuntime(device=dev)
        if not dev.enabled:
            rt.status = DeviceStatus.DISABLED
        self.runtimes[dev.id] = rt
        if dev.enabled and self._running:
            rt.task = asyncio.create_task(self._loop(rt), name=f"poll-{dev.id}")
        return rt

    def _ensure_driver(self, rt: DeviceRuntime) -> Driver:
        if rt.driver is None or (rt.driver.host, rt.driver.port) != (rt.device.host, rt.device.port):
            rt.driver = driver_for(rt.device, self.http, timeout=self.settings.current.polling.timeout_s)
        return rt.driver

    async def add_from_probe(self, probe: ProbeResult, *, name: str | None = None, tags: list[str] | None = None,
                             group: str | None = None) -> AddResult:
        existing = await self.store.find_device(probe.info)
        if existing:
            rt = self.runtimes.get(existing.id)
            if rt:
                async with rt.lock:
                    if rt.removing or self.runtimes.get(existing.id) is not rt:
                        raise KeyError(existing.id)
                    return await _complete(asyncio.create_task(
                        self._merge_probe(rt.device.model_copy(deep=True), probe, rt)
                    ))
            return await self._merge_probe(existing, probe, None)
        dev = await self.store.add_device(probe.info, name=name, tags=tags, group=group)
        self._spawn(dev)
        await self.events.emit("device_added", f"Added {dev.name}", severity=Severity.INFO, device_id=dev.id,
                               data={"host": dev.host, "model": dev.model})
        return AddResult(dev, created=True)

    async def _merge_probe(self, existing: Device, probe: ProbeResult, rt: DeviceRuntime | None) -> AddResult:
        check_identity(existing, probe.info)
        note = None
        merged = False
        if probe.info.host not in (existing.host, *existing.alt_hosts):
            existing.alt_hosts.append(probe.info.host)
            await self.store.save_device(existing)
            note = f"{existing.name} also answers on {probe.info.host}; it is the same miner, so it was not added twice."
            merged = True
            if rt:
                rt.device = existing
        return AddResult(existing, created=False, merged=merged, note=note or f"{existing.name} is already being monitored.")

    async def add_by_host(self, host: str, port: int | None = None, *, name: str | None = None, tags: list[str] | None = None,
                          group: str | None = None, drivers: list[str] | None = None) -> AddResult:
        found = await probe_host(host, port, client=self.http, timeout=min(6.0, self.settings.current.polling.timeout_s),
                                 drivers=drivers)
        if not found:
            raise LookupError(
                f"Nothing at {host}{':' + str(port) if port else ''} looks like a supported miner. "
                "Check the address, that the miner is on and on this network, and see the supported list in the docs."
            )
        return await self.add_from_probe(found[0], name=name, tags=tags, group=group)

    async def remove(self, device_id: str, *, keep_history: bool = False) -> bool:
        rt = self.runtimes.get(device_id)
        if rt is None or rt.removing:
            return False
        rt.removing = True
        try:
            async with rt.lock:
                return await _complete(asyncio.create_task(self._remove_locked(rt, keep_history)))
        finally:
            rt.removing = False

    async def _remove_locked(self, rt: DeviceRuntime, keep_history: bool) -> bool:
        device_id = rt.device.id
        async with self._sample_lock:
            if keep_history:
                await self._flush_samples_locked()
            await self.store.delete_device(device_id, keep_history=keep_history)
            self._pending = [row for row in self._pending if row["device_id"] != device_id]
            self.runtimes.pop(device_id)
            self._summary_cache = None
        if rt.task:
            rt.task.cancel()
            await asyncio.gather(rt.task, return_exceptions=True)
        if rt.driver:
            with contextlib.suppress(Exception):
                await rt.driver.close()
        await self.events.emit("device_removed", f"Removed {rt.device.name}", device_id=None, data={"host": rt.device.host})
        self.bus.publish("device_removed", {"id": device_id})
        return True

    async def update(self, device_id: str, patch: dict[str, Any]) -> Device:
        rt = self.runtimes.get(device_id)
        if rt is None:
            raise KeyError(device_id)
        async with rt.lock:
            if rt.removing or self.runtimes.get(device_id) is not rt:
                raise KeyError(device_id)
            if self._stopping:
                raise PermissionError("The monitor is stopping.")
            return await _complete(asyncio.create_task(self._update_locked(rt, patch)))

    async def _update_locked(self, rt: DeviceRuntime, patch: dict[str, Any]) -> Device:
        allowed = {"name", "tags", "group", "notes", "enabled", "allow_control", "poll_interval_s", "model_override", "host", "port"}
        unknown = set(patch) - allowed - {"power_override_w"}
        if unknown:
            raise ValueError(f"cannot change: {', '.join(sorted(unknown))}")
        dev = Device.model_validate({**rt.device.model_dump(), **{key: patch[key] for key in allowed & set(patch)}})
        if "power_override_w" in patch:
            if patch["power_override_w"] in (None, 0):
                dev.extra.pop("power_override_w", None)
            else:
                power = float(patch["power_override_w"])
                if not math.isfinite(power) or not 0 <= power <= 20000:
                    raise ValueError("power override must be between 0 and 20000 W")
                dev.extra["power_override_w"] = power
        if not dev.name.strip():
            raise ValueError("name cannot be empty")
        if not dev.host.strip() or not 1 <= dev.port <= 65535:
            raise ValueError("a miner needs a host and port (1-65535)")
        if dev.poll_interval_s is not None and not 2 <= dev.poll_interval_s <= 3600:
            raise ValueError("poll interval must be between 2 and 3600 seconds")
        try:
            await self.store.save_device(dev)
        except sqlite3.IntegrityError as e:
            raise ValueError("another miner already uses that endpoint") from e
        rt.device = dev
        if {"host", "port", "power_override_w"} & set(patch):
            old_driver = rt.driver
            rt.driver = None
            if old_driver:
                await old_driver.close()
        # start/stop polling when enabled flips
        if "enabled" in patch:
            if dev.enabled and self._running and (rt.task is None or rt.task.done()):
                rt.status = DeviceStatus.UNKNOWN
                rt.task = asyncio.create_task(self._loop(rt), name=f"poll-{dev.id}")
            elif not dev.enabled:
                if rt.task:
                    rt.task.cancel()
                rt.status = DeviceStatus.DISABLED
                rt.status_since = time.time()
        rt.wake.set()
        self.bus.publish("device", {"id": dev.id, "view": self.view(dev.id).model_dump(mode="json")})  # type: ignore[union-attr]
        return dev

    # -- views ------------------------------------------------------------------------------------------------

    def view(self, device_id: str) -> DeviceView | None:
        rt = self.runtimes.get(device_id)
        if rt is None:
            return None
        d = rt.device
        spark = list(rt.spark)[-SPARK_POINTS:]
        return DeviceView(
            **d.model_dump(),
            status=rt.status,
            status_since=rt.status_since,
            status_reason=rt.status_reason,
            consecutive_failures=rt.failures,
            last_error=rt.last_error,
            telemetry=rt.telemetry,
            web_url=None if d.driver == "sim" else (f"http://{d.host}" if d.driver == "axeos" else None),
            hashrate_smooth_hs=rt.hashrate_smooth,
            spark_hashrate_hs=spark,
            last_poll_ms=rt.last_poll_ms,
        )

    def views(self) -> list[DeviceView]:
        out = [v for v in (self.view(i) for i in self.runtimes) if v is not None]
        out.sort(key=lambda v: (v.name.lower(), v.id))
        return out

    def summary(self, *, fresh: bool = False) -> FleetSummary:
        if fresh or self._summary_cache is None:
            self._summary_cache = build_summary(list(self.runtimes.values()), self.settings.current, demo=self.demo)
        return self._summary_cache

    def all_addresses(self) -> list[str]:
        """Payout addresses to watch for blocks: configured ones plus whatever the miners point at."""
        seen: list[str] = []
        for a in self.settings.current.mining.addresses:
            if a not in seen:
                seen.append(a)
        for rt in self.runtimes.values():
            for p in (rt.telemetry.pools if rt.telemetry else []):
                if p.address and p.address not in seen and parse_address(p.address):
                    seen.append(p.address)
        return seen

    # -- polling -----------------------------------------------------------------------------------------------------

    def _interval_for(self, rt: DeviceRuntime) -> float:
        cfg = self.settings.current.polling
        base = rt.device.poll_interval_s or cfg.interval_s
        if rt.failures <= 0:
            return base
        if rt.failures < cfg.offline_after_failures:
            return min(base, 5.0) if base > 5 else base  # retry soon before declaring a device dead
        # exponential back-off for long outages: offline_interval, x2, x4 ... capped at 5 minutes
        steps = min(4, rt.failures - cfg.offline_after_failures)
        return min(300.0, max(cfg.offline_interval_s, base) * float(2**steps))

    async def _loop(self, rt: DeviceRuntime) -> None:
        try:
            await asyncio.sleep(random.uniform(0.0, min(4.0, self.settings.current.polling.interval_s)))
            while self._running:
                started = time.monotonic()
                await self._poll_once(rt)
                delay = max(0.5, self._interval_for(rt) - (time.monotonic() - started))
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(rt.wake.wait(), timeout=delay)
                rt.wake.clear()
        except asyncio.CancelledError:
            raise
        except Exception:  # pragma: no cover - last-resort guard; the loop must never die silently
            log.exception("polling loop for %s crashed", rt.device.name)

    async def poll_now(self, device_id: str) -> DeviceView:
        rt = self.runtimes.get(device_id)
        if rt is None:
            raise KeyError(device_id)
        await self._poll_once(rt)
        return self.view(device_id)  # type: ignore[return-value]

    async def _poll_once(self, rt: DeviceRuntime) -> None:
        async with rt.lock:
            if self._stopping or rt.removing or self.runtimes.get(rt.device.id) is not rt:
                return
            await self._poll_locked(rt)

    async def _poll_locked(self, rt: DeviceRuntime) -> None:
        cfg = self.settings.current.polling
        async with self._sem:
            t0 = time.monotonic()
            try:
                driver = self._ensure_driver(rt)
                telemetry = await asyncio.wait_for(driver.poll(), timeout=cfg.timeout_s + 4)
            except (DriverError, TimeoutError, OSError) as e:
                rt.last_poll_ms = (time.monotonic() - t0) * 1000
                await self._on_failure(rt, e)
                return
            except Exception as e:
                log.exception("unexpected error polling %s", rt.device.name)
                rt.last_poll_ms = (time.monotonic() - t0) * 1000
                await self._on_failure(rt, e)
                return
            rt.last_poll_ms = (time.monotonic() - t0) * 1000
        await self._on_success(rt, telemetry)

    async def _on_failure(self, rt: DeviceRuntime, error: Exception) -> None:
        cfg = self.settings.current.polling
        now = time.time()
        rt.failures += 1
        rt.last_error = str(error) or error.__class__.__name__
        if isinstance(error, IdentityMismatch):
            rt.failures = max(rt.failures, cfg.offline_after_failures)
        restarting = now < rt.expect_back_until and not isinstance(error, IdentityMismatch)
        if restarting:
            self._set_status(rt, DeviceStatus.DEGRADED, "Restarting")
        elif rt.failures >= cfg.offline_after_failures and rt.status != DeviceStatus.OFFLINE:
            rt.offline_since = now
            await self._set_status_async(rt, DeviceStatus.OFFLINE, rt.last_error)
        if rt.failures >= cfg.offline_after_failures or restarting:
            # one row per failed poll lets availability be computed later
            self._pending.append(telemetry_to_row(rt.device.id, Telemetry(ts=now, online=False)))
        self.bus.publish("device", {"id": rt.device.id, "view": self.view(rt.device.id).model_dump(mode="json")})  # type: ignore[union-attr]

    async def _on_success(self, rt: DeviceRuntime, t: Telemetry) -> None:
        now = time.time()
        prev = rt.telemetry
        t.ts = now
        if t.efficiency_j_th is None:
            t.efficiency_j_th = compute_efficiency(t.power_w, t.hashrate_hs)
        if t.reject_rate_pct is None:
            t.reject_rate_pct = compute_reject_rate(t.shares_accepted, t.shares_rejected)
        was_offline = rt.status == DeviceStatus.OFFLINE
        recovered_after = (now - rt.offline_since) if (was_offline and rt.offline_since) else None
        rt.failures = 0
        rt.last_error = None
        rt.offline_since = None
        rt.telemetry = t
        rt.last_ok_ts = now
        rt.last_seen_dirty = True
        rt.device.last_seen_at = now
        self._smooth(rt, t, prev, now)
        self._accumulate_work(rt, t, prev, now)
        self._pending.append(telemetry_to_row(rt.device.id, t))

        status, reason = derive_status(t, self.settings.current)
        if was_offline:
            await self.events.emit(
                "device_online", f"{rt.device.name} is back online", severity=Severity.SUCCESS, device_id=rt.device.id,
                body=f"It was unreachable for {mining_duration(recovered_after)}." if recovered_after else None,
            )
        await self._set_status_async(rt, status, reason)
        await self._detect_events(rt, prev, t)
        self.bus.publish("device", {"id": rt.device.id, "view": self.view(rt.device.id).model_dump(mode="json")})  # type: ignore[union-attr]

    def _smooth(self, rt: DeviceRuntime, t: Telemetry, prev: Telemetry | None, now: float) -> None:
        hr = t.hashrate_hs
        rt.spark.append(hr)
        if hr is None:
            return
        if rt.hashrate_smooth is None or prev is None:
            rt.hashrate_smooth = hr
            return
        dt = max(0.1, now - prev.ts)
        alpha = 1 - math.exp(-dt / SMOOTHING_TAU_S)
        rt.hashrate_smooth += alpha * (hr - rt.hashrate_smooth)

    def _accumulate_work(self, rt: DeviceRuntime, t: Telemetry, prev: Telemetry | None, now: float) -> None:
        if prev is None or t.hashrate_hs is None or t.hashrate_hs <= 0:
            return
        dt = now - prev.ts
        cap = 3 * max(self.settings.current.polling.interval_s, 5.0)
        dt = min(max(dt, 0.0), cap)
        hashes = t.hashrate_hs * dt
        self._work_hashes += hashes
        diff = self.difficulty_provider()
        if diff:
            self._work_blocks += mining.work_to_expected_blocks(hashes, diff)
        self._work_dirty = True

    @property
    def work(self) -> tuple[float, float]:
        """(total hashes performed while monitored, expected blocks of work at the difficulty of the day)"""
        return self._work_hashes, self._work_blocks

    def _set_status(self, rt: DeviceRuntime, status: DeviceStatus, reason: str | None) -> None:
        if rt.status != status:
            rt.status = status
            rt.status_since = time.time()
        rt.status_reason = reason

    async def _set_status_async(self, rt: DeviceRuntime, status: DeviceStatus, reason: str | None) -> None:
        old = rt.status
        self._set_status(rt, status, reason)
        if old == status:
            return
        name = rt.device.name
        if status == DeviceStatus.OFFLINE:
            await self.events.emit("device_offline", f"{name} is offline", severity=Severity.CRITICAL, device_id=rt.device.id,
                                   body=reason, data={"host": rt.device.host})
        elif status == DeviceStatus.DEGRADED and old in (DeviceStatus.ONLINE, DeviceStatus.UNKNOWN):
            await self.events.emit("device_degraded", f"{name} needs attention", severity=Severity.WARNING, device_id=rt.device.id,
                                   body=reason, dedupe_key=f"degraded:{rt.device.id}", dedupe_window_s=600)
        elif status == DeviceStatus.ONLINE and old == DeviceStatus.DEGRADED:
            await self.events.emit("device_recovered", f"{name} is healthy again", severity=Severity.SUCCESS, device_id=rt.device.id)
        elif status == DeviceStatus.PAUSED:
            await self.events.emit("device_paused", f"{name} was paused", device_id=rt.device.id)

    async def _detect_events(self, rt: DeviceRuntime, prev: Telemetry | None, t: Telemetry) -> None:
        dev = rt.device
        name = dev.name
        if prev is not None:
            if t.uptime_s is not None and prev.uptime_s is not None and t.uptime_s + 30 < prev.uptime_s:
                await self.events.emit("device_restarted", f"{name} restarted", severity=Severity.INFO, device_id=dev.id,
                                       data={"previous_uptime_s": prev.uptime_s})
            if prev.using_fallback is False and t.using_fallback:
                await self.events.emit("pool_failover", f"{name} switched to its fallback pool", severity=Severity.WARNING,
                                       device_id=dev.id, body="It is no longer mining to your primary pool.")
            elif prev.using_fallback and t.using_fallback is False:
                await self.events.emit("pool_restored", f"{name} is back on its primary pool", severity=Severity.SUCCESS, device_id=dev.id)
            if t.blocks_found is not None and prev.blocks_found is not None and t.blocks_found > prev.blocks_found:
                await self.events.emit(
                    "block_found", f"{name} reports it found a block!", severity=Severity.SUCCESS, device_id=dev.id,
                    body="The miner's own block counter went up. Confirm on the Blocks page once the node sees it.",
                    data={"source": "device", "blocks_found": t.blocks_found},
                )
                self.bus.publish("block_found", {"device_id": dev.id, "source": "device"})
        # personal best share
        if t.best_diff:
            prev_best = prev.best_diff if prev else None
            if prev_best is None:
                known = await self.store.best_shares_leaderboard(500)
                prev_best = next((r["difficulty"] for r in known if r["device_id"] == dev.id), None)
                if prev_best is None:
                    await self.store.add_best_share(dev.id, t.best_diff)  # baseline, no celebration
                    prev_best = t.best_diff
            if t.best_diff > prev_best * 1.000001:
                diff = self.difficulty_provider()
                await self.store.add_best_share(dev.id, t.best_diff)
                prog = t.best_diff / diff if diff else None
                await self.events.emit(
                    "new_best_share", f"New best share on {name}", severity=Severity.SUCCESS, device_id=dev.id,
                    body=f"Difficulty {_si(t.best_diff)} (was {_si(prev_best)})."
                         + (f" That is {prog * 100:.4f}% of the way to a block." if prog else ""),
                    data={"difficulty": t.best_diff, "previous": prev_best, "progress": prog},
                    dedupe_key=f"best:{dev.id}", dedupe_window_s=60,
                )
        if t.firmware and dev.firmware and t.firmware != dev.firmware:
            old_fw = dev.firmware
            dev.firmware = t.firmware
            await self.store.save_device(dev)
            await self.events.emit("firmware_changed", f"{name} is now running {t.firmware}", severity=Severity.INFO,
                                   device_id=dev.id, body=f"It was running {old_fw}.", data={"from": old_fw, "to": t.firmware})
        elif t.firmware and not dev.firmware:
            dev.firmware = t.firmware
            await self.store.save_device(dev)

    # -- background loops ----------------------------------------------------------------------------------------------

    async def _flush_samples(self) -> None:
        async with self._sample_lock:
            await _complete(asyncio.create_task(self._flush_samples_locked()))

    async def _flush_samples_locked(self) -> None:
        if not self._pending:
            return
        rows, self._pending = self._pending, []
        try:
            # Raw rows and every rollup share one commit. Nested SampleStore tx calls join it.
            async with self.store.db.tx():
                await self.store.samples.write(rows)
        except BaseException:
            log.exception("could not write %d samples; keeping them for the next attempt", len(rows))
            self._pending = rows + self._pending
            raise

    async def _writer_loop(self) -> None:
        while self._running:
            await asyncio.sleep(5)
            try:
                await self._flush_samples()
            except Exception:
                log.exception("sample writer will retry the retained batch")

    async def _flush_misc(self, force: bool = False) -> None:
        if self._work_dirty or force:
            await self.store.kv_set("luck.total_hashes", self._work_hashes)
            await self.store.kv_set("luck.expected_blocks", self._work_blocks)
            self._work_dirty = False
        dirty = [rt for rt in self.runtimes.values() if rt.last_seen_dirty]
        for rt in dirty:
            rt.last_seen_dirty = False
            await self.store.touch_device(rt.device.id, rt.device.last_seen_at)

    async def _housekeeping_loop(self) -> None:
        last_prune = 0.0
        while self._running:
            await asyncio.sleep(30)
            try:
                await self._flush_misc()
                if time.time() - last_prune > 3600:
                    last_prune = time.time()
                    r = self.settings.current.retention
                    from bsmm.storage.samples import Retention

                    await self.store.samples.prune(Retention(r.raw_days, r.minute_days, r.hour_days))
                    await self.store.prune_events(r.event_days)
                    await self.store.purge_sessions()
            except Exception:
                log.exception("housekeeping failed")

    async def _summary_loop(self) -> None:
        while self._running:
            self._summary_cache = build_summary(list(self.runtimes.values()), self.settings.current, demo=self.demo)
            self.bus.publish("fleet", self._summary_cache.model_dump(mode="json"))
            await asyncio.sleep(4)

    # -- control -----------------------------------------------------------------------------------------------------------

    async def run_action(self, device_id: str, action: str, params: dict[str, Any] | None = None, *, actor: str = "user",
                         dry_run: bool = False) -> dict[str, Any]:
        """Execute a control action with guard rails; always audited."""
        rt = self.runtimes.get(device_id)
        if rt is None:
            raise KeyError(device_id)
        async with rt.lock:
            if rt.removing or self.runtimes.get(device_id) is not rt:
                raise KeyError(device_id)
            if self._stopping:
                raise PermissionError("The monitor is stopping.")
            return await _complete(asyncio.create_task(
                self._run_action_locked(device_id, action, params, actor=actor, dry_run=dry_run)
            ))

    async def _run_action_locked(self, device_id: str, action: str, params: dict[str, Any] | None, *, actor: str,
                                 dry_run: bool) -> dict[str, Any]:
        params = params or {}
        rt = self.runtimes.get(device_id)
        if rt is None:
            raise KeyError(device_id)
        cfg = self.settings.current.safety
        dev = rt.device
        if not cfg.allow_control:
            raise PermissionError("Controlling miners is switched off in Settings > Safety.")
        if not dev.allow_control:
            raise PermissionError(f"Control is switched off for {dev.name}.")
        if not dev.enabled:
            raise PermissionError(f"{dev.name} is disabled.")
        needed = {
            "restart": Capability.RESTART,
            "identify": Capability.IDENTIFY,
            "pause": Capability.PAUSE,
            "resume": Capability.PAUSE,
            "set_pool": Capability.SET_POOL,
            "set_fan": Capability.SET_FAN,
            "set_tuning": Capability.SET_FREQUENCY,
        }
        if action not in needed:
            raise ValueError(f"unknown action {action!r}; valid: {', '.join(sorted(needed))}")
        if needed[action] not in dev.capabilities:
            raise Unsupported(f"{dev.name} ({dev.display_model}) does not support '{action}' through this app.")
        if action == "set_tuning" and not cfg.allow_tuning:
            raise PermissionError("Frequency/voltage changes are switched off. Enable them in Settings > Safety first.")
        if action == "set_tuning":
            t = rt.telemetry
            if t and t.temp_asic_c and t.temp_asic_c >= cfg.max_temp_c:
                raise ActionFailed(f"{dev.name} is already at {t.temp_asic_c:.0f} C; cool it down before tuning.")
        driver = self._ensure_driver(rt)
        try:
            await driver.validate_action(action, params)
        except (DriverError, ValueError, TypeError) as e:
            if not dry_run:
                await self.store.add_audit(actor, action, dev.id, params, {"ok": False, "error": str(e)})
            raise
        if dry_run:
            return {"ok": True, "dry_run": True, "action": action, "device": dev.name, "params": _redact(params)}
        try:
            await driver.verify_identity()
            # Settings can change during a read-only identity/range request.
            if not self.settings.current.safety.allow_control or not dev.allow_control or rt.removing:
                raise PermissionError("Control was switched off or the miner is being removed.")
            if action == "set_tuning" and not self.settings.current.safety.allow_tuning:
                raise PermissionError("Frequency/voltage changes are switched off.")
            if action == "restart":
                res = await driver.restart()
                rt.expect_back_until = time.time() + RESTART_GRACE_S
            elif action == "identify":
                res = await driver.identify()
            elif action == "pause":
                res = await driver.pause()
            elif action == "resume":
                res = await driver.resume()
            elif action == "set_pool":
                res = await driver.set_pool(
                    url=params.get("url", ""), port=params.get("port", 0), user=params.get("user", ""),
                    password=params.get("password", "x"), role=params.get("role", "primary"), tls=params.get("tls"),
                )
            elif action == "set_fan":
                res = await driver.set_fan(auto=params.get("auto"), speed_pct=params.get("speed_pct"),
                                           temp_target_c=params.get("temp_target_c"))
            else:
                res = await driver.set_tuning(frequency_mhz=params.get("frequency_mhz"), core_voltage_mv=params.get("core_voltage_mv"))
        except (DriverError, ValueError, TypeError) as e:
            await self.store.add_audit(actor, action, dev.id, params, {"ok": False, "error": str(e)})
            raise
        await self.store.add_audit(actor, action, dev.id, params, {"ok": res.ok, "message": res.message})
        rt.wake.set()
        return {"ok": res.ok, "action": action, "device": dev.name, "message": res.message}


def _redact(params: dict[str, Any]) -> dict[str, Any]:
    return {k: ("***" if "pass" in k.lower() else v) for k, v in params.items()}


def mining_duration(seconds: float | None) -> str:
    from bsmm.units import format_duration

    return format_duration(seconds)


def _si(v: float) -> str:
    from bsmm.units import format_si

    return format_si(v, "")
