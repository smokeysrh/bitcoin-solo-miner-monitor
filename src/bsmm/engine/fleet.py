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
from bsmm.drivers.base import Driver, DriverError, check_identity
from bsmm.drivers.registry import driver_for, probe_host
from bsmm.engine import pool_watch
from bsmm.engine.bus import EventBus
from bsmm.engine.events import EventLog
from bsmm.models import (
    Device,
    DeviceStatus,
    DeviceView,
    FleetSummary,
    PoolChange,
    PoolUsage,
    PoolWatchRow,
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
MONITOR_RETRY_MAX_S = 300.0
MONITOR_RETRY_MAX_STEPS = 5
#: Most unsaved sample rows kept in memory while storage is failing (a few MB; hours for a home fleet).
MAX_PENDING_SAMPLES = 10_000

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
    spark: deque[float | None] = field(default_factory=lambda: deque(maxlen=SPARK_POINTS * 3))
    last_seen_dirty: bool = False
    offline_since: float | None = None
    #: consecutive poll iterations that failed after the miner answered (storage/event errors)
    monitor_failures: int = 0
    #: a change of the pool or payout settings that the user has not answered yet (shown as a badge)
    pool_change: PoolChange | None = None
    #: consecutive polls reporting the same not-yet-confirmed pool settings (the same idea as ``failures``)
    pool_sightings: pool_watch.PoolSightings = field(default_factory=pool_watch.PoolSightings)


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
        # A paused miner draws nothing (AxeOS reports 0 W, which the driver maps to None): known zero, not missing.
        power_w = 0.0 if t.power_w is None and rt.status == DeviceStatus.PAUSED else t.power_w
        if power_w is None:
            s.devices_without_power += 1
        else:
            power += power_w
            have_power = True
            if power_w and hr_s > 0:
                eff_power += power_w
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
        self._sample_write_failing = False
        self._samples_dropped = 0
        self._dropped_ts: tuple[int, int] | None = None
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
        self._work_hashes = float(await self.store.kv_get("luck.total_hashes", 0.0))
        self._work_blocks = float(await self.store.kv_get("luck.expected_blocks", 0.0))
        if await self.store.kv_get("luck.since") is None:
            await self.store.kv_set("luck.since", time.time())
        for dev in await self.store.list_devices():
            self._spawn(dev)  # not running yet, so no poll task exists until the waiting pool changes are rebuilt
        await self._load_pool_changes()
        self._running = True
        for rt in self.runtimes.values():
            if rt.device.enabled and rt.task is None:
                self._start_polling(rt)
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

    def adopt(self, dev: Device) -> DeviceRuntime:
        """Start monitoring a device that is already saved (a committed config import)."""
        return self._spawn(dev)

    def _spawn(self, dev: Device) -> DeviceRuntime:
        rt = DeviceRuntime(device=dev)
        if not dev.enabled:
            rt.status = DeviceStatus.DISABLED
        self.runtimes[dev.id] = rt
        if dev.enabled and self._running:
            self._start_polling(rt)
        return rt

    def _start_polling(self, rt: DeviceRuntime) -> None:
        rt.task = asyncio.create_task(self._loop(rt), name=f"poll-{rt.device.id}")

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
        allowed = {"name", "tags", "group", "notes", "enabled", "poll_interval_s", "model_override", "host", "port"}
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

    async def relocate_endpoint(self, device_id: str, host: str, port: int, *, from_endpoint: tuple[str, int],
                                same_miner: Callable[[Device], bool]) -> Device | None:
        """Move an offline miner to the address where its identity turned up (automatic IP healing).

        The caller scans without any lock; every condition is rechecked here under the device lock. Returns ``None`` and
        changes nothing when the miner was removed, edited, brought back, or no longer matches in the meantime.
        """
        rt = self.runtimes.get(device_id)
        if rt is None:
            return None
        async with rt.lock:
            if rt.removing or self._stopping or self.runtimes.get(device_id) is not rt:
                return None
            return await _complete(asyncio.create_task(self._relocate_locked(rt, host, port, from_endpoint, same_miner)))

    async def _relocate_locked(self, rt: DeviceRuntime, host: str, port: int, from_endpoint: tuple[str, int],
                               same_miner: Callable[[Device], bool]) -> Device | None:
        dev = rt.device
        if rt.status != DeviceStatus.OFFLINE or (dev.host, dev.port) != from_endpoint or not same_miner(dev):
            return None
        if any(other is not rt and (other.device.host, other.device.port) == (host, port) for other in self.runtimes.values()):
            return None
        candidate = dev.model_copy(deep=True)
        candidate.host, candidate.port = host, port
        if dev.host not in candidate.alt_hosts:
            candidate.alt_hosts.append(dev.host)
        await self.store.save_device(candidate)  # persist first: a failure leaves the runtime untouched
        rt.device = candidate
        old_driver, rt.driver = rt.driver, None
        if old_driver:
            try:
                await old_driver.close()
            except Exception:
                log.warning("closing the old driver of %s failed", candidate.name, exc_info=True)
        rt.wake.set()
        return candidate

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
            pool_change=rt.pool_change,
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

    def _monitor_retry_delay(self, rt: DeviceRuntime) -> float:
        """Back-off after an iteration failed for a reason other than the miner not answering."""
        base = rt.device.poll_interval_s or self.settings.current.polling.interval_s
        return min(MONITOR_RETRY_MAX_S, base * float(2 ** min(rt.monitor_failures - 1, MONITOR_RETRY_MAX_STEPS)))

    def _note_monitor_failure(self, rt: DeviceRuntime, error: Exception) -> None:
        """Make a failed iteration visible without touching storage or blaming the miner."""
        log.exception("polling iteration for %s failed (attempt %d); retrying", rt.device.name, rt.monitor_failures)
        if rt.status == DeviceStatus.OFFLINE:
            return  # the miner's own failure is already what the user sees
        rt.last_error = str(error) or error.__class__.__name__
        self._set_status(rt, DeviceStatus.DEGRADED, "Readings could not be saved; trying again")
        view = self.view(rt.device.id)
        if view is not None:  # tiles and detail update from this topic, not from REST
            self.bus.publish("device", {"id": rt.device.id, "view": view.model_dump(mode="json")})

    async def _loop(self, rt: DeviceRuntime) -> None:
        try:
            await asyncio.sleep(random.uniform(0.0, min(4.0, self.settings.current.polling.interval_s)))
            while self._running:
                started = time.monotonic()
                try:
                    await self._poll_once(rt)
                except Exception as e:
                    # Not a driver failure (those are handled in _poll_locked): a storage or event write
                    # failed after the read. Keep the task alive; cancellation is not an Exception.
                    rt.monitor_failures += 1
                    self._note_monitor_failure(rt, e)
                    delay = self._monitor_retry_delay(rt)
                else:
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
        rt.pool_sightings.reset()  # a poll that failed ends any run of identical pool readings
        # An identity mismatch counts like any other failed poll: one odd reading must not flip a working miner
        # offline (#92). A replaced miner still mismatches on every poll, so it reaches the threshold anyway.
        if rt.failures >= cfg.offline_after_failures and rt.status != DeviceStatus.OFFLINE:
            rt.offline_since = now
            await self._set_status_async(rt, DeviceStatus.OFFLINE, rt.last_error)
        if rt.failures >= cfg.offline_after_failures:
            # one row per failed poll lets availability be computed later
            self._pending.append(telemetry_to_row(rt.device.id, Telemetry(ts=now, online=False)))
            self._bound_pending()
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
        self._bound_pending()

        status, reason = derive_status(t, self.settings.current)
        if rt.monitor_failures:
            # An earlier iteration failed after its read. Announce status changes (recovery, back online)
            # only once the rest of this iteration has completed, so a persistent failure cannot repeat them.
            await self._detect_events(rt, prev, t)
            await self._announce_status(rt, was_offline, recovered_after, status, reason)
        else:
            await self._announce_status(rt, was_offline, recovered_after, status, reason)
            await self._detect_events(rt, prev, t)
        rt.monitor_failures = 0
        self.bus.publish("device", {"id": rt.device.id, "view": self.view(rt.device.id).model_dump(mode="json")})  # type: ignore[union-attr]

    async def _announce_status(
        self, rt: DeviceRuntime, was_offline: bool, recovered_after: float | None, status: DeviceStatus, reason: str | None,
    ) -> None:
        if was_offline:
            await self.events.emit(
                "device_online", f"{rt.device.name} is back online", severity=Severity.SUCCESS, device_id=rt.device.id,
                body=f"It was unreachable for {mining_duration(recovered_after)}." if recovered_after else None,
            )
        await self._set_status_async(rt, status, reason)

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
        await self._watch_pool_settings(rt, t)

    # -- pool and payout settings (safety alert; reads only, HashHurdr's own record is the only thing written) ------------

    async def _load_pool_changes(self) -> None:
        """After a restart, show the badge again for every change that is still waiting for the user's answer.

        What the notice shows comes from the event, so it is the same whether the miner still reports the new settings
        or has gone back to the recorded ones.
        """
        for row in await self.store.list_pool_changes():
            rt = self.runtimes.get(row.device_id)
            if rt is None or row.event_id is None:
                continue
            event = await self.store.get_event(row.event_id)
            if event is None:  # event retention keeps it while the change waits, so this is not expected
                log.warning("pool settings event %s of device %s is missing; its notice cannot be shown", row.event_id, row.device_id)
                continue
            rt.pool_change = PoolChange(event_id=row.event_id, since_ts=row.changed_ts or row.baseline_ts,
                                        changes=pool_watch.changes_of(event.model_dump(mode="json")))

    async def _watch_pool_settings(self, rt: DeviceRuntime, t: Telemetry) -> None:
        """Compare what the miner reports with HashHurdr's baseline; raise one event for a confirmed change.

        The first reading becomes the baseline without an alert. Settings that differ must then be reported by
        ``offline_after_failures`` polls in a row (the count that also decides when a miner is offline) before they count:
        one odd reading, an empty pool list, or a poll that failed does not. The event and the record change in one
        transaction, so a failure leaves nothing half done and the next poll tries again.

        A confirmed change stays open until the user answers it, also when the miner reports the baseline again. That
        return is recorded once (``observed`` is cleared, the event stays), after which a steady reading of either the
        baseline or the unanswered settings is the usual poll that writes nothing.
        """
        current = pool_watch.fingerprint(t.pools)
        if not current:  # the miner reported no pool at all: no evidence either way, and it ends any run of readings
            rt.pool_sightings.reset()
            return
        now = time.time()
        known = await self.store.get_pool_watch(rt.device.id)
        if known is not None and current == known.confirmed:  # the usual poll: nothing to write, so no transaction
            rt.pool_sightings.reset()
            return
        async with self.store.db.tx():
            row = await self.store.get_pool_watch(rt.device.id)  # read again inside the transaction that may change it
            if row is None:
                await self.store.save_pool_watch(PoolWatchRow(device_id=rt.device.id, baseline=current, baseline_ts=now))
                rt.pool_sightings.reset()
                return
            if current == row.confirmed:
                rt.pool_sightings.reset()
                return
            if rt.pool_sightings.note(current) < self.settings.current.polling.offline_after_failures:
                return
            rt.pool_sightings.reset()
            changes = pool_watch.diff(row.baseline, current)
            if not changes:  # back on the recorded settings: an open change stays open, only the return is noted
                if row.observed is not None:
                    await self.store.save_pool_watch(row.model_copy(update={"observed": None}))
                return
            if row.event_id is not None:  # the answer to an earlier change is replaced by this one
                await self.store.ack_event(row.event_id)
            event = await self.events.emit(
                pool_watch.EVENT_TYPE, pool_watch.event_title(rt.device.name), severity=Severity.CRITICAL,
                device_id=rt.device.id, body=pool_watch.describe_changes(changes, short=False),
                data={"changes": [c.model_dump() for c in changes]},
            )
            if event is None or event.id is None:
                raise RuntimeError("the pool settings event was not stored")
            await self.store.save_pool_watch(row.model_copy(update={"observed": current, "event_id": event.id, "changed_ts": now}))
            opened = PoolChange(event_id=event.id, since_ts=now, changes=changes)
        rt.pool_change = opened

    async def accept_pool_change(self, device_id: str, event_id: int) -> DeviceView:
        """The user says the settings HashHurdr last confirmed are normal: they become its baseline.

        The event is resolved. Those settings are the unanswered changed ones, or the recorded baseline after a
        confirmed return to it. The miner's current report is not read. Only HashHurdr's own record changes. No
        driver is used, so nothing is sent to the miner.
        """
        rt = self.runtimes.get(device_id)
        if rt is None:
            raise KeyError(device_id)
        async with rt.lock:
            if rt.removing or self.runtimes.get(device_id) is not rt:
                raise KeyError(device_id)
            if self._stopping:
                raise PermissionError("The monitor is stopping.")
            return await _complete(asyncio.create_task(self._accept_pool_change_locked(rt, event_id)))

    async def _accept_pool_change_locked(self, rt: DeviceRuntime, event_id: int) -> DeviceView:
        async with self.store.db.tx():
            row = await self.store.get_pool_watch(rt.device.id)
            if row is None or row.event_id != event_id:
                raise pool_watch.PoolChangeNotPending(event_id)
            reported = row.observed if row.observed is not None else row.baseline  # after a return: the recorded settings
            await self.store.save_pool_watch(row.model_copy(update={
                "baseline": reported, "baseline_ts": time.time(), "observed": None, "event_id": None, "changed_ts": None}))
            await self.store.ack_event(event_id)
        rt.pool_change = None
        rt.pool_sightings.reset()
        view = self.view(rt.device.id)
        if view is None:  # cannot happen while the device lock is held; kept explicit instead of an assert
            raise KeyError(rt.device.id)
        self.bus.publish("device", {"id": view.id, "view": view.model_dump(mode="json")})
        return view

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
            self._sample_write_failing = True
            self._bound_pending()
            raise
        self._sample_write_failing = False

    def _bound_pending(self) -> None:
        """Keep at most MAX_PENDING_SAMPLES unsaved rows. Discard the oldest and remember the gap."""
        excess = len(self._pending) - MAX_PENDING_SAMPLES
        if excess <= 0:
            return
        stamps = [row["ts"] for row in self._pending[:excess]]
        lo, hi = min(stamps), max(stamps)
        if self._dropped_ts is not None:
            lo, hi = min(lo, self._dropped_ts[0]), max(hi, self._dropped_ts[1])
        self._dropped_ts = (lo, hi)
        self._samples_dropped += excess
        del self._pending[:excess]
        log.warning("sample backlog is full; discarded the %d oldest unsaved samples", excess)

    @property
    def sample_storage(self) -> dict[str, Any]:
        """Health of sample persistence: failing now, backlog size and any gap left by discarded samples."""
        return {
            "failing": self._sample_write_failing,
            "backlog": len(self._pending),
            "dropped": self._samples_dropped,
            "dropped_from_ts": self._dropped_ts[0] if self._dropped_ts else None,
            "dropped_to_ts": self._dropped_ts[1] if self._dropped_ts else None,
        }

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


def mining_duration(seconds: float | None) -> str:
    from bsmm.units import format_duration

    return format_duration(seconds)


def _si(v: float) -> str:
    from bsmm.units import format_si

    return format_si(v, "")
