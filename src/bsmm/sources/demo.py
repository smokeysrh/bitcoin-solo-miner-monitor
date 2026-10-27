"""Plausible, self-contained network data for demo mode (no internet, no node needed)."""

from __future__ import annotations

import time
from typing import ClassVar

from bsmm.sources.base import (
    BlockInfo,
    ConnectionTest,
    DataSource,
    NetworkSnapshot,
    NodeStatus,
    PoolStatus,
    PoolWorker,
)

BASE_HEIGHT = 972_175
DIFFICULTY = 140_577_680_051_919.6
NET_HASHRATE = 1.0325e21
EX_ADDR = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
_T0 = time.time()


def _height(now: float) -> int:
    return BASE_HEIGHT + int((now - _T0) // 600)


class DemoSource(DataSource):
    kind: ClassVar[str] = "demo"
    label: ClassVar[str] = "Demo data"

    async def network(self) -> NetworkSnapshot | None:
        now = time.time()
        h = _height(now)
        tip_time = _T0 + (h - BASE_HEIGHT) * 600 - 90
        pools = ["Foundry USA", "AntPool", "ViaBTC", "MARA Pool", "F2Pool", "Luxor"]
        blocks = [
            BlockInfo(hash=f"{(h - i):064x}", height=h - i, ts=tip_time - i * 600, tx_count=3200 + 90 * i, pool_name=pools[i % len(pools)],
                      reward_sats=312_500_000 + 9_000_000 + i * 700_000, fees_sats=9_000_000 + i * 700_000,
                      coinbase_addresses=["bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"])
            for i in range(8)
        ]
        return NetworkSnapshot(
            source="demo", ts=now, height=h, tip_hash=blocks[0].hash, tip_time=tip_time, difficulty=DIFFICULTY,
            network_hashrate_hs=NET_HASHRATE, epoch_start_time=tip_time - (h % 2016) * 598,
            mempool_tx_count=24_500, mempool_vsize=18_200_000,
            fees_sat_vb={"fastest": 5.0, "half_hour": 4.0, "hour": 3.0, "economy": 2.0, "minimum": 1.0},
            prices={"USD": 82_000.0, "EUR": 73_100.0, "GBP": 61_600.0}, recent_blocks=blocks,
        )

    async def node(self) -> NodeStatus | None:
        h = _height(time.time())
        return NodeStatus(
            reachable=True, version="29.0.0", subversion="/Satoshi:29.0.0/", chain="main", blocks=h, headers=h,
            initial_block_download=False, verification_progress=0.99999, connections=18, connections_in=6, connections_out=12,
            mempool_tx_count=24_500, mempool_bytes=18_200_000, mempool_max_bytes=300_000_000, min_relay_fee_sat_vb=1.0,
            size_on_disk=780_000_000_000, pruned=False, uptime_s=int(time.time() - _T0) + 12 * 86400, network_active=True,
            difficulty=DIFFICULTY, network_hashrate_hs=NET_HASHRATE,
        )

    async def pool(self, addresses: list[str]) -> list[PoolStatus]:
        now = time.time()
        workers = [PoolWorker(name=n, hashrate_hs=hr, best_difficulty=bd, last_seen=now - 12, started=now - 86400 * 9)
                   for n, hr, bd in (("gamma1", 1.15e12, 2.1e9), ("nerdqaxe1", 4.8e12, 5.1e10), ("avalon1", 3.9e12, 8.3e9))]
        return [PoolStatus(kind="public_pool", name="Demo Public Pool", reachable=True, pool_hashrate_hs=sum(w.hashrate_hs or 0 for w in workers),
                           pool_miners=len(workers), blocks_found=0, address=addresses[0] if addresses else EX_ADDR,
                           hashrate_hs=sum(w.hashrate_hs or 0 for w in workers), best_difficulty=5.1e10, best_difficulty_ever=5.1e10,
                           workers=workers, last_share=now - 12)]

    async def test(self) -> ConnectionTest:
        return ConnectionTest(ok=True, message="Demo data is always available.")
