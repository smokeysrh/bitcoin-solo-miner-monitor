"""mempool.space (or your own mempool instance, e.g. the Umbrel/Start9 app) as a network data source."""

from __future__ import annotations

import asyncio
import time
from typing import Any, ClassVar, NamedTuple

from bsmm.sources.base import (
    BlockInfo,
    ConnectionTest,
    DataSource,
    NetworkSnapshot,
    SourceBadResponse,
    SourceError,
    fetch_json,
)
from bsmm.units import to_float, to_int

DEFAULT_URL = "https://mempool.space"


class SoloPool(NamedTuple):
    slug: str  # mempool.space's pool slug, as in /api/v1/mining/pool/{slug}/blocks
    name: str


#: The solo pools mempool.space labels on blocks today. The one place to add another.
SOLO_POOLS: tuple[SoloPool, ...] = (
    SoloPool("solock", "Solo CK"),
    SoloPool("publicpool", "Public Pool"),
    SoloPool("braiinssolo", "Braiins Solo"),
    SoloPool("futurebitapollosolo", "FutureBit Apollo Solo"),
    SoloPool("solopoolcom", "SoloPool.com"),
)


class MempoolSpaceSource(DataSource):
    kind: ClassVar[str] = "mempool_space"
    label: ClassVar[str] = "mempool.space (public or self-hosted)"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._hashrate_cache: tuple[float, float | None] | None = None

    @property
    def base(self) -> str:
        return (self.source.url or DEFAULT_URL).rstrip("/")

    async def _get(self, path: str) -> Any:
        return await fetch_json(self.client, f"{self.base}{path}", timeout=self.timeout)

    async def _text(self, path: str) -> str:
        return str(await fetch_json(self.client, f"{self.base}{path}", timeout=self.timeout, accept_text=True)).strip()

    @staticmethod
    def parse_block(b: dict[str, Any]) -> BlockInfo:
        extras = b.get("extras") or {}
        pool = extras.get("pool") or {}
        addresses = extras.get("coinbaseAddresses")
        if not isinstance(addresses, list):
            addresses = [a for a in [extras.get("coinbaseAddress")] if a]
        return BlockInfo(
            hash=str(b.get("id", "")),
            height=int(b.get("height", 0)),
            ts=float(b.get("timestamp", 0)),
            tx_count=to_int(b.get("tx_count")),
            pool_name=pool.get("name") if isinstance(pool, dict) else None,
            reward_sats=to_int(extras.get("reward")),
            fees_sats=to_int(extras.get("totalFees")),
            coinbase_addresses=[str(a) for a in addresses],
        )

    async def block_info(self, height: int) -> BlockInfo | None:
        """A block by height (two requests), for a gap older than the recent list. None if the lookup fails."""
        try:
            bhash = await self._text(f"/api/block-height/{height}")
            data = await self._get(f"/api/v1/block/{bhash}")
            if not bhash or not isinstance(data, dict) or data.get("id") != bhash:
                return None
            block = self.parse_block(data)
        except (SourceError, ValueError, TypeError):
            return None
        if block.height != height:
            return None
        # A looked-up block with an empty address list is a verified result, not a missing one.
        block.coinbase_complete = isinstance((data.get("extras") or {}).get("coinbaseAddresses"), list)
        return block

    async def pool_blocks(self, slug: str) -> list[BlockInfo]:
        """The newest blocks mempool.space attributes to one pool (one request). Raises SourceError if unreadable."""
        data = await self._get(f"/api/v1/mining/pool/{slug}/blocks")
        if not isinstance(data, list) or not all(isinstance(b, dict) for b in data):
            raise SourceBadResponse(f"the block list for pool {slug!r} was not a list of blocks")
        try:
            return [self.parse_block(b) for b in data]
        except (ValueError, TypeError) as e:
            raise SourceBadResponse(f"a block in the list for pool {slug!r} could not be read ({e})") from e

    async def _network_hashrate(self) -> float | None:
        """3-day network hashrate; the payload is large so it is cached for 30 minutes."""
        now = time.monotonic()
        if self._hashrate_cache and now - self._hashrate_cache[0] < 1800:
            return self._hashrate_cache[1]
        try:
            data = await self._get("/api/v1/mining/hashrate/3d")
            value = to_float(data.get("currentHashrate")) if isinstance(data, dict) else None
        except SourceError:
            value = self._hashrate_cache[1] if self._hashrate_cache else None
        self._hashrate_cache = (now, value)
        return value

    async def network(self) -> NetworkSnapshot | None:
        results = await asyncio.gather(
            self._get("/api/v1/blocks"),
            self._get("/api/v1/difficulty-adjustment"),
            self._get("/api/v1/prices"),
            self._get("/api/v1/fees/recommended"),
            self._get("/api/mempool"),
            self._network_hashrate(),
            return_exceptions=True,
        )
        blocks_r, adj_r, prices_r, fees_r, mempool_r, hashrate_r = results
        snap = NetworkSnapshot(source=f"mempool_space:{self.base}")
        if isinstance(blocks_r, SourceError) and isinstance(adj_r, SourceError):
            raise blocks_r  # nothing useful: surface the real error
        if isinstance(blocks_r, list) and blocks_r:
            blocks = [self.parse_block(b) for b in blocks_r if isinstance(b, dict)]
            snap.recent_blocks = blocks
            tip = blocks_r[0]
            snap.height = to_int(tip.get("height"))
            snap.tip_hash = tip.get("id")
            snap.tip_time = to_float(tip.get("timestamp"))
            snap.difficulty = to_float(tip.get("difficulty"))
        if isinstance(adj_r, dict):
            snap.est_difficulty_change_pct = to_float(adj_r.get("difficultyChange"))
            est = to_float(adj_r.get("estimatedRetargetDate"))
            snap.est_retarget_ts = est / 1000.0 if est else None
            if snap.height is None and to_int(adj_r.get("nextRetargetHeight")) is not None:
                snap.height = to_int(adj_r["nextRetargetHeight"]) - to_int(adj_r.get("remainingBlocks"), 0)  # type: ignore[operator]
        if isinstance(prices_r, dict):
            snap.prices = {k: float(v) for k, v in prices_r.items() if k != "time" and isinstance(v, int | float)}
        if isinstance(fees_r, dict):
            snap.fees_sat_vb = {
                "fastest": to_float(fees_r.get("fastestFee")) or 0.0,
                "half_hour": to_float(fees_r.get("halfHourFee")) or 0.0,
                "hour": to_float(fees_r.get("hourFee")) or 0.0,
                "economy": to_float(fees_r.get("economyFee")) or 0.0,
                "minimum": to_float(fees_r.get("minimumFee")) or 0.0,
            }
        if isinstance(mempool_r, dict):
            snap.mempool_tx_count = to_int(mempool_r.get("count"))
            snap.mempool_vsize = to_int(mempool_r.get("vsize"))
        if isinstance(hashrate_r, float):
            snap.network_hashrate_hs = hashrate_r
        return snap

    async def test(self) -> ConnectionTest:
        try:
            height = int(await self._text("/api/blocks/tip/height"))
        except (SourceError, ValueError) as e:
            return ConnectionTest(
                ok=False,
                message=f"Could not read {self.base}: {e}",
                hints=["Check the address (for a self-hosted mempool use e.g. http://umbrel.local:3006).", "This source needs no password."],
            )
        return ConnectionTest(ok=True, message=f"Connected. Chain tip is block {height:,}.", details={"height": height})
