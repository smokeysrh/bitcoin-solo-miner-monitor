"""Bitcoin network awareness: node + pool + public APIs merged into one state, plus block detection.

Source priority for the headline numbers: your own node, then your pool's node, then
mempool.space, then whatever the miners themselves report. Lower-priority sources still fill gaps
(for example the BTC price) so one flaky source never blanks the dashboard.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

from bsmm import mining
from bsmm.engine.bus import EventBus
from bsmm.engine.events import EventLog
from bsmm.models import Severity, Source
from bsmm.settings import SettingsService
from bsmm.sources.base import (
    BlockInfo,
    ConnectionTest,
    DataSource,
    NetworkSnapshot,
    NodeStatus,
    PoolStatus,
    SourceError,
)
from bsmm.sources.bitcoin_core import BitcoinCoreSource
from bsmm.sources.ckpool import CkpoolSource
from bsmm.sources.demo import DemoSource
from bsmm.sources.mempool_space import MempoolSpaceSource
from bsmm.sources.public_pool import PublicPoolSource
from bsmm.storage.store import Store, new_id

log = logging.getLogger(__name__)

SOURCE_CLASSES: dict[str, type[DataSource]] = {
    BitcoinCoreSource.kind: BitcoinCoreSource,
    PublicPoolSource.kind: PublicPoolSource,
    CkpoolSource.kind: CkpoolSource,
    MempoolSpaceSource.kind: MempoolSpaceSource,
    DemoSource.kind: DemoSource,
}
PRIORITY = {"demo": -1, "bitcoin_core": 0, "public_pool": 1, "mempool_space": 2, "device": 3}
POLL_EVERY = {"demo": 15.0, "bitcoin_core": 12.0, "public_pool": 30.0, "mempool_space": 60.0, "ckpool": 60.0}
PUBLIC_SOURCE_ID = "public-mempool"
STALE_AFTER_S = 600
BLOCK_CHECK_BATCH = 60


class _M(BaseModel):
    model_config = ConfigDict(extra="ignore")


class SourceHealth(_M):
    id: str
    kind: str
    name: str
    ok: bool | None = None  # None = not polled yet
    error: str | None = None
    last_ok: float | None = None
    last_poll: float | None = None
    implicit: bool = False


class FieldSource(_M):
    source: str
    ts: float
    stale: bool


class NetworkState(_M):
    updated_at: float = 0.0
    available: bool = False
    source: str | None = None
    height: int | None = None
    tip_hash: str | None = None
    tip_time: float | None = None
    difficulty: float | None = None
    network_hashrate_hs: float | None = None
    block_reward_btc: float | None = None
    subsidy_btc: float | None = None
    avg_fees_btc: float | None = None
    epoch: dict[str, Any] | None = None
    halving: dict[str, Any] | None = None
    mempool_tx_count: int | None = None
    mempool_vsize: int | None = None
    fees_sat_vb: dict[str, float] | None = None
    prices: dict[str, float] | None = None
    btc_price: float | None = None
    recent_blocks: list[BlockInfo] = Field(default_factory=list)
    node: NodeStatus | None = None
    pools: list[PoolStatus] = Field(default_factory=list)
    sources: list[SourceHealth] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    stale: bool = False
    field_sources: dict[str, FieldSource] = Field(default_factory=dict)
    node_behind_by: int | None = None


@dataclass(slots=True)
class _Poller:
    source: Source
    impl: DataSource
    implicit: bool = False
    next_due: float = 0.0
    health: SourceHealth | None = None
    snapshot: NetworkSnapshot | None = None
    node: NodeStatus | None = None
    pools: list[PoolStatus] = field(default_factory=list)


class NetworkService:
    def __init__(self, store: Store, settings: SettingsService, bus: EventBus, events: EventLog, http: httpx.AsyncClient,
                 *, offline: bool = False, demo: bool = False, watch_addresses: Any = None) -> None:
        self.store = store
        self.settings = settings
        self.bus = bus
        self.events = events
        self.http = http
        self.offline = offline
        self.demo = demo
        #: callable returning the payout addresses to watch (provided by the app: fleet + settings)
        self.watch_addresses: Any = watch_addresses or (lambda: [])
        self.state = NetworkState()
        self._pollers: dict[str, _Poller] = {}
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._device_snapshot: NetworkSnapshot | None = None
        self._device_dirty = False
        self._last_height: int | None = None
        self._last_difficulty: float | None = None
        self._lock = asyncio.Lock()

    # -- lifecycle ------------------------------------------------------------------------------------

    async def start(self) -> None:
        self._running = True
        await self.reload_sources()
        self.settings.on_change(lambda new, old: asyncio.create_task(self.reload_sources()))
        self._task = asyncio.create_task(self._loop(), name="network-service")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)

    async def reload_sources(self) -> None:
        async with self._lock:
            sources = await self.store.list_sources()
            keep: dict[str, _Poller] = {}
            for src in sources:
                if not src.enabled or src.kind not in SOURCE_CLASSES:
                    continue
                old = self._pollers.get(src.id)
                if old and old.source == src:
                    keep[src.id] = old
                    continue
                secret = await self.store.source_secret(src.id)
                keep[src.id] = _Poller(src, SOURCE_CLASSES[src.kind](src, secret, self.http), health=SourceHealth(
                    id=src.id, kind=src.kind, name=src.name))
            cfg = self.settings.current.network
            if self.demo:
                demo_src = Source(id="demo-data", kind="demo", name="Demo data")
                keep["demo-data"] = self._pollers.get("demo-data") or _Poller(
                    demo_src, DemoSource(demo_src, {}, self.http), implicit=True,
                    health=SourceHealth(id="demo-data", kind="demo", name="Demo data", implicit=True))
            elif cfg.use_public_apis and not self.offline and not any(p.source.kind == "mempool_space" for p in keep.values()):
                pub = Source(id=PUBLIC_SOURCE_ID, kind="mempool_space", name="mempool.space (public)", url=cfg.mempool_url)
                old = self._pollers.get(PUBLIC_SOURCE_ID)
                if old and old.source.url == pub.url:
                    keep[PUBLIC_SOURCE_ID] = old
                else:
                    keep[PUBLIC_SOURCE_ID] = _Poller(pub, MempoolSpaceSource(pub, {}, self.http), implicit=True,
                                                     health=SourceHealth(id=pub.id, kind=pub.kind, name=pub.name, implicit=True))
            self._pollers = keep
        for p in self._pollers.values():
            p.next_due = 0.0

    # -- manual use by the API / wizard -----------------------------------------------------------------

    async def test_source(self, kind: str, url: str | None, secret: dict[str, str], options: dict[str, Any] | None = None) -> ConnectionTest:
        if kind not in SOURCE_CLASSES:
            return ConnectionTest(ok=False, message=f"Unknown source type {kind!r}.")
        src = Source(id="test", kind=kind, name="test", url=url, options=options or {})
        try:
            return await SOURCE_CLASSES[kind](src, secret, self.http).test()
        except ValueError as e:
            return ConnectionTest(ok=False, message=str(e))
        except SourceError as e:
            return ConnectionTest(ok=False, message=str(e))

    async def add_source(self, kind: str, name: str, url: str | None, secret: dict[str, str] | None, options: dict[str, Any] | None) -> Source:
        if kind not in SOURCE_CLASSES:
            raise ValueError(f"unknown source type {kind!r}")
        src = Source(id=new_id("src"), kind=kind, name=name or SOURCE_CLASSES[kind].label, url=url, options=options or {},
                     has_secret=bool(secret))
        await self.store.save_source(src, secret=secret or {})
        await self.reload_sources()
        self.refresh_soon()
        return src

    def refresh_soon(self) -> None:
        for p in self._pollers.values():
            p.next_due = 0.0

    def difficulty(self) -> float | None:
        return self.state.difficulty

    def set_device_snapshot(self, height: int | None, difficulty: float | None, *, ts: float | None = None) -> None:
        """Last-resort figures the miners report themselves (AxeOS firmware 2.x includes them)."""
        if difficulty:
            snapshot = NetworkSnapshot(source="device", height=height, difficulty=difficulty,
                                       ts=ts if ts is not None else time.time())
            if snapshot != self._device_snapshot:
                self._device_snapshot = snapshot
                self._device_dirty = True

    # -- polling --------------------------------------------------------------------------------------------

    async def _loop(self) -> None:
        while self._running:
            try:
                due = [p for p in self._pollers.values() if p.next_due <= time.monotonic()]
                if due:
                    await asyncio.gather(*(self._poll(p) for p in due))
                    await self._merge()
                elif self._device_dirty or (self._device_snapshot and not self.state.stale
                                            and time.time() - self._device_snapshot.ts > STALE_AFTER_S):
                    await self._merge()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("network service iteration failed")
            await asyncio.sleep(2)

    async def _poll(self, p: _Poller) -> None:
        kind = p.source.kind
        p.next_due = time.monotonic() + POLL_EVERY.get(kind, 60.0)
        h = p.health
        assert h is not None
        was_failing = h.ok is False
        h.last_poll = time.time()
        try:
            addresses = list(self.watch_addresses())
            if kind == "demo":
                p.node = await p.impl.node()
                p.snapshot = await p.impl.network()
                p.pools = await p.impl.pool(addresses)
                h.ok, h.error = True, None
            elif kind == "bitcoin_core":
                p.node = await p.impl.node()
                p.snapshot = await p.impl.network() if p.node and p.node.reachable and not p.node.error else None
                h.ok = bool(p.node and p.node.reachable and not p.node.error)
                h.error = None if h.ok else (p.node.error if p.node else "no answer")
            elif kind == "public_pool":
                p.snapshot = await p.impl.network()
                p.pools = await p.impl.pool(addresses)
                h.ok = p.snapshot is not None
                h.error = None if h.ok else "unexpected reply"
            elif kind == "ckpool":
                p.pools = await p.impl.pool(addresses)
                h.ok = any(x.reachable for x in p.pools) if p.pools else True
                h.error = None if h.ok else (p.pools[0].error if p.pools else None)
            else:
                p.snapshot = await p.impl.network()
                h.ok = p.snapshot is not None
                h.error = None if h.ok else "unexpected reply"
        except SourceError as e:
            h.ok, h.error = False, str(e)
        except Exception as e:  # a buggy/odd response must not take the loop down
            log.exception("source %s failed", p.source.name)
            h.ok, h.error = False, f"{e.__class__.__name__}: {e}"
        if h.ok:
            h.last_ok = time.time()
            if was_failing:
                await self.events.emit("source_up", f"{p.source.name} is reachable again", severity=Severity.SUCCESS,
                                       data={"source_id": p.source.id})
        else:
            await self.events.emit("source_down", f"Can't reach {p.source.name}", severity=Severity.WARNING,
                                   body=h.error, dedupe_key=f"source:{p.source.id}", dedupe_window_s=3600,
                                   data={"source_id": p.source.id})

    async def _merge(self) -> None:
        # Clear before any await; an observation arriving during this merge remains dirty.
        self._device_dirty = False
        pollers = list(self._pollers.values())
        snaps: list[tuple[tuple[bool, int], NetworkSnapshot]] = []
        now = time.time()
        for p in pollers:
            if p.snapshot:
                stale = not (p.health and p.health.ok) or now - p.snapshot.ts > STALE_AFTER_S
                snaps.append(((stale, PRIORITY.get(p.source.kind, 5)), p.snapshot))
        if self._device_snapshot:
            snaps.append(((now - self._device_snapshot.ts > STALE_AFTER_S, PRIORITY["device"]), self._device_snapshot))
        snaps.sort(key=lambda t: t[0])
        st = NetworkState(updated_at=time.time())
        if snaps:
            primary = snaps[0][1]
            st.source = primary.source
            for field_name in ("height", "tip_hash", "tip_time", "difficulty", "network_hashrate_hs", "mempool_tx_count",
                               "mempool_vsize", "fees_sat_vb", "prices"):
                for (stale, _), s in snaps:
                    v = getattr(s, field_name)
                    if v is not None:
                        setattr(st, field_name, v)
                        st.field_sources[field_name] = FieldSource(source=s.source, ts=s.ts, stale=stale)
                        break
            st.available = st.difficulty is not None
            if "difficulty" in st.field_sources:
                st.source = st.field_sources["difficulty"].source
            blocks: dict[str, BlockInfo] = {}
            for _, s in reversed(snaps):
                for b in s.recent_blocks:
                    blocks[b.hash] = b
            st.recent_blocks = sorted(blocks.values(), key=lambda b: -b.height)[:12]
            st.warnings = [w for _, s in snaps for w in s.warnings]
            est_pct = next((s.est_difficulty_change_pct for _, s in snaps if s.est_difficulty_change_pct is not None), None)
            epoch_start = next((s.epoch_start_time for _, s in snaps if s.epoch_start_time is not None), None)
            est_ts = next((s.est_retarget_ts for _, s in snaps if s.est_retarget_ts is not None), None)
            if st.height is not None:
                ep = mining.epoch_info(st.height, epoch_start, st.tip_time)
                d = ep.as_dict()
                if epoch_start is None and est_pct is not None:
                    d["estimated_change_pct"] = est_pct
                if epoch_start is None and est_ts is not None:
                    from datetime import UTC, datetime

                    d["estimated_date"] = datetime.fromtimestamp(est_ts, UTC).isoformat()
                    d["seconds_remaining"] = max(0.0, est_ts - time.time())
                st.epoch = d
                st.halving = mining.halving_info(st.height).as_dict()
                st.subsidy_btc = mining.subsidy_sats(st.height) / mining.SATS_PER_BTC
                fees = self._avg_fees_btc(st)
                st.avg_fees_btc = fees
                st.block_reward_btc = st.subsidy_btc + (fees or 0.0)
        cfg = self.settings.current.network
        if cfg.price_source == "manual" and cfg.manual_btc_price:
            st.btc_price = cfg.manual_btc_price
        elif cfg.price_source == "mempool" and st.prices:
            cur = self.settings.current.units.currency.upper()
            st.btc_price = st.prices.get(cur) or st.prices.get("USD")
        for p in pollers:
            if p.node:
                st.node = p.node
                break
        st.pools = [pool for p in pollers for pool in p.pools]
        st.sources = [p.health for p in pollers if p.health]
        ref_height = next((snap.height for p in pollers if p.source.kind == "mempool_space" and (snap := p.snapshot) and snap.height), None)
        if st.node and st.node.blocks is not None and ref_height:
            behind = ref_height - st.node.blocks
            st.node_behind_by = max(0, behind)
        st.stale = any(st.field_sources[f].stale for f in ("height", "difficulty") if f in st.field_sources)
        async with self._lock:
            old_h, old_d = self._last_height, self._last_difficulty
            self.state = st
        await self._after_merge(st, old_h, old_d)
        self.bus.publish("network", st.model_dump(mode="json", exclude={"recent_blocks"}))

    def _avg_fees_btc(self, st: NetworkState) -> float | None:
        override = self.settings.current.network.avg_block_fees_btc
        if override is not None:
            return override
        vals: list[float] = []
        for b in st.recent_blocks[:10]:
            if b.fees_sats is not None:
                vals.append(b.fees_sats / 1e8)
            elif b.reward_sats is not None:
                fees = b.reward_sats - mining.subsidy_sats(b.height)
                if fees >= 0:
                    vals.append(fees / 1e8)
        return sum(vals) / len(vals) if vals else None

    async def _after_merge(self, st: NetworkState, old_height: int | None, old_diff: float | None) -> None:
        if st.height is None:
            return
        self._last_height = st.height
        if old_diff and st.difficulty and abs(st.difficulty - old_diff) / old_diff > 1e-9:
            pct = (st.difficulty / old_diff - 1) * 100
            await self.events.emit(
                "difficulty_adjusted", f"Difficulty {'rose' if pct > 0 else 'fell'} {abs(pct):.2f}%", severity=Severity.INFO,
                body=f"Network difficulty is now {st.difficulty:.4g}.", data={"old": old_diff, "new": st.difficulty, "pct": pct},
            )
        if st.difficulty:
            self._last_difficulty = st.difficulty
        if old_height is None:
            # First look since the app started. Keep the saved marker, so a block that arrived while the app was not
            # running is still checked; a fresh install has no marker yet and simply starts from here.
            marker = await self.store.kv_get("blocks.last_checked")
            if marker is None:
                await self.store.kv_set("blocks.last_checked", st.height)
            elif st.height > int(marker):
                await self._check_blocks(st, int(marker))
            return
        if st.height > old_height:
            self.bus.publish("new_block", {"height": st.height, "hash": st.tip_hash})
        # A failed detail read must also be retried at an unchanged tip.
        await self._check_blocks(st, old_height)

    async def _check_blocks(self, st: NetworkState, old_height: int) -> None:
        last_checked = int(await self.store.kv_get("blocks.last_checked", old_height))
        if st.height is None or st.height <= last_checked:
            return
        watch = set(self.watch_addresses())
        by_height = {b.height: b for b in st.recent_blocks}
        core = next((p.impl for p in self._pollers.values() if isinstance(p.impl, BitcoinCoreSource)), None)
        for h in range(last_checked + 1, min(st.height, last_checked + BLOCK_CHECK_BATCH) + 1):
            block = by_height.get(h)
            if (block is None or not (block.coinbase_addresses or block.coinbase_complete)) and core is not None:
                block = await core.block_info(h)
            if block is None or not (block.coinbase_addresses or block.coinbase_complete):
                log.warning("Block %s payout details unresolved; will retry without advancing the checked height", h)
                break
            mine = sorted(watch.intersection(block.coinbase_addresses))
            if mine:
                await self.record_block_found(block, mine[0], source="chain")
            await self.store.kv_set("blocks.last_checked", h)

    async def record_block_found(self, block: BlockInfo, address: str | None, *, source: str, device_id: str | None = None) -> bool:
        new = await self.store.add_block_found(
            hash_=block.hash, height=block.height, ts=block.ts, device_id=device_id, address=address,
            reward_sats=block.reward_sats, source=source, data={"pool": block.pool_name, "tx_count": block.tx_count},
        )
        if not new:
            return False
        await self.events.emit(
            "block_found", "YOU FOUND A BLOCK!", severity=Severity.SUCCESS,
            body=f"Block {block.height:,} matches watched address {address}. This is monitoring evidence, not confirmation of a payout amount." if address else f"Block {block.height:,}.",
            data={"height": block.height, "hash": block.hash, "reward_sats": block.reward_sats, "address": address, "source": source},
            dedupe_key=f"block:{block.hash}",
        )
        self.bus.publish("block_found", {"height": block.height, "hash": block.hash, "address": address, "source": source})
        return True

    async def close_pollers(self) -> None:
        with contextlib.suppress(Exception):
            await self.stop()
