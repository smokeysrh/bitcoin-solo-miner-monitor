"""The latest blocks found by solo pools, from mempool.space (Solo blocks page, ``GET /api/v1/blocks/solo``).

mempool.space labels the pool on every block and lists a pool's newest blocks at
``/api/v1/mining/pool/{slug}/blocks``. This merges the lists of the pools in ``SOLO_POOLS`` into one,
newest first, and caches the result: solo pools find a handful of blocks a year, so asking again within
half an hour would only add load. Whether a block is the user's own is decided by the route, from the same
found-block records as ``/blocks/recent``.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from pydantic import BaseModel, Field

from bsmm.engine.network import NetworkService
from bsmm.sources.base import BlockInfo, SourceError
from bsmm.sources.demo import demo_solo_blocks
from bsmm.sources.mempool_space import DEFAULT_URL, SOLO_POOLS, MempoolSpaceSource, SoloPool

log = logging.getLogger(__name__)

SOLO_BLOCKS_LIMIT = 20
#: A complete list is reused this long (about 27 solo blocks a year: nothing changes minute to minute).
SOLO_BLOCKS_CACHE_S = 1800.0
#: A list that is missing a pool is asked for again sooner, but still not on every page view.
SOLO_BLOCKS_PARTIAL_CACHE_S = 300.0


class SoloBlocksUnavailable(SourceError):
    """Every pool list failed: there is nothing to show, and that is not the same as "no blocks"."""

    code = "solo_blocks_unavailable"


class SoloBlock(BaseModel):
    hash: str
    height: int
    ts: float
    pool_slug: str
    pool_name: str
    tx_count: int | None = None
    url: str
    yours: bool = False  # set by the route, from the user's own found blocks


class SoloBlocksResult(BaseModel):
    #: False when outside lookups are off: ``message`` says so in plain words and ``blocks`` is not a finding
    available: bool = True
    message: str | None = None
    blocks: list[SoloBlock] = Field(default_factory=list)
    source: str | None = None
    fetched_at: float | None = None
    #: True when a refresh failed and ``blocks`` is the last good list; ``error`` says why
    stale: bool = False
    error: str | None = None
    #: pools whose list could not be read, so ``blocks`` may be missing some of their blocks
    failed_pools: list[str] = Field(default_factory=list)


def merge_solo_blocks(by_pool: Mapping[SoloPool, Sequence[BlockInfo]], limit: int = SOLO_BLOCKS_LIMIT) -> list[SoloBlock]:
    """One list, newest first (by height), each block once, at most ``limit`` of them."""
    seen: dict[str, SoloBlock] = {}
    for pool, blocks in by_pool.items():
        for b in blocks:
            if b.hash not in seen:
                seen[b.hash] = SoloBlock(
                    hash=b.hash, height=b.height, ts=b.ts, pool_slug=pool.slug, pool_name=pool.name, tx_count=b.tx_count,
                    url=f"{DEFAULT_URL}/block/{b.hash}")
    return sorted(seen.values(), key=lambda b: (-b.height, -b.ts, b.hash))[:limit]


@dataclass(slots=True)
class _Cached:
    base: str
    expires: float
    result: SoloBlocksResult


class SoloBlocksService:
    def __init__(self, network: NetworkService, *, clock: Callable[[], float] = time.monotonic) -> None:
        self.network = network
        #: monotonic seconds; replaceable so tests can move time
        self.clock = clock
        self._cache: _Cached | None = None
        self._lock = asyncio.Lock()

    async def get(self) -> SoloBlocksResult:
        """The list, from the cache when fresh. Raises ``SoloBlocksUnavailable`` if nothing can be shown."""
        if self.network.demo:
            return SoloBlocksResult(blocks=merge_solo_blocks(demo_solo_blocks(time.time())), source="demo", fetched_at=time.time())
        source = self.network.mempool_source()
        if source is None:
            return SoloBlocksResult(available=False, message=self._why_off())
        async with self._lock:  # a second visitor waits for the first lookup instead of repeating it
            cached = self._cache if self._cache and self._cache.base == source.base else None
            if cached and self.clock() < cached.expires:
                return cached.result
            try:
                fresh = await self._fetch(source)
            except SoloBlocksUnavailable as e:
                if cached:
                    log.warning("Solo blocks refresh failed, serving the last list: %s", e)
                    return cached.result.model_copy(update={"stale": True, "error": str(e)})
                raise
            self._cache = fresh
            return fresh.result

    async def _fetch(self, source: MempoolSpaceSource) -> _Cached:
        lists = await asyncio.gather(*(source.pool_blocks(p.slug) for p in SOLO_POOLS), return_exceptions=True)
        by_pool: dict[SoloPool, list[BlockInfo]] = {}
        failed: list[tuple[SoloPool, SourceError]] = []
        for pool, outcome in zip(SOLO_POOLS, lists, strict=True):
            if isinstance(outcome, SourceError):
                failed.append((pool, outcome))
            elif isinstance(outcome, BaseException):
                raise outcome  # not a lookup problem: a bug must not be shown as "no blocks"
            else:
                by_pool[pool] = outcome
        if not by_pool:
            raise SoloBlocksUnavailable(f"Could not read solo-pool blocks from {source.base}: {failed[0][1]}")
        for pool, err in failed:
            log.warning("Solo blocks: could not read %s from %s: %s", pool.name, source.base, err)
        ttl = SOLO_BLOCKS_PARTIAL_CACHE_S if failed else SOLO_BLOCKS_CACHE_S
        result = SoloBlocksResult(
            blocks=merge_solo_blocks(by_pool), source=source.base, fetched_at=time.time(), failed_pools=[p.name for p, _ in failed])
        return _Cached(base=source.base, expires=self.clock() + ttl, result=result)

    def _why_off(self) -> str:
        if self.network.offline:
            return "This app is running in offline mode, so it does not ask mempool.space for solo-pool blocks."
        if not self.network.settings.current.network.use_public_apis:
            return "Outside lookups are turned off. Turn on “Use mempool.space” in Settings > Node & pool to list solo-pool blocks."
        return "No mempool.space source is connected yet. Add one in Settings > Node & pool to list solo-pool blocks."
