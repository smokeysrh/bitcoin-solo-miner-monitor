"""Public Pool (https://github.com/benjamin-wilson/public-pool): the solo pool shipped as an Umbrel /
Start9 app. Its REST API needs no credentials and also tells us the node's network state.

Endpoints used: ``/api/network``, ``/api/pool``, ``/api/info``, ``/api/client/{address}``.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, ClassVar

from bsmm.sources.base import (
    ConnectionTest,
    DataSource,
    NetworkSnapshot,
    PoolStatus,
    PoolWorker,
    SourceError,
    fetch_json,
)
from bsmm.units import parse_difficulty, to_float, to_int


def _iso_to_ts(value: Any) -> float | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


class PublicPoolSource(DataSource):
    kind: ClassVar[str] = "public_pool"
    label: ClassVar[str] = "Public Pool (Umbrel / Start9 / self-hosted)"

    @property
    def base(self) -> str:
        url = (self.source.url or "").strip().rstrip("/")
        return url[:-4] if url.endswith("/api") else url

    async def _get(self, path: str) -> Any:
        return await fetch_json(self.client, f"{self.base}{path}", timeout=self.timeout)

    async def network(self) -> NetworkSnapshot | None:
        data = await self._get("/api/network")
        if not isinstance(data, dict) or "difficulty" not in data:
            return None
        return NetworkSnapshot(
            source=f"public_pool:{self.base}",
            height=to_int(data.get("blocks")),
            difficulty=to_float(data.get("difficulty")),
            network_hashrate_hs=to_float(data.get("networkhashps")),
            mempool_tx_count=to_int(data.get("pooledtx")),
            warnings=[str(w) for w in data.get("warnings", []) if w],
        )

    async def pool(self, addresses: list[str]) -> list[PoolStatus]:
        pool_r: Any
        info_r: Any
        pool_r, info_r = await asyncio.gather(self._get("/api/pool"), self._get("/api/info"), return_exceptions=True)
        if isinstance(pool_r, SourceError):
            return [PoolStatus(kind=self.kind, name=self.source.name, reachable=False, error=str(pool_r))]
        base = PoolStatus(kind=self.kind, name=self.source.name, reachable=True)
        if isinstance(pool_r, dict):
            base.pool_hashrate_hs = to_float(pool_r.get("totalHashRate"))
            base.pool_miners = to_int(pool_r.get("totalMiners"))
            found = pool_r.get("blocksFound")
            base.blocks_found = len(found) if isinstance(found, list) else to_int(found)
            base.extra["fee_pct"] = pool_r.get("fee")
            base.extra["block_height"] = pool_r.get("blockHeight")
        if isinstance(info_r, dict):
            base.blocks = [b for b in info_r.get("blockData", []) if isinstance(b, dict)]
            if base.blocks_found is None:
                base.blocks_found = len(info_r.get("blockData", []))
            scores = info_r.get("highScores")
            if isinstance(scores, list) and scores and isinstance(scores[0], dict):
                base.extra["pool_best_difficulty"] = to_float(scores[0].get("bestDifficulty"))
            base.extra["user_agents"] = info_r.get("userAgents", [])
        if not addresses:
            return [base]
        out: list[PoolStatus] = []
        for addr in addresses:
            st = base.model_copy(deep=True)
            st.address = addr
            try:
                client = await self._get(f"/api/client/{addr}")
            except SourceError as e:
                st.error = f"address stats unavailable: {e}"
                out.append(st)
                continue
            if isinstance(client, dict):
                st.best_difficulty = parse_difficulty(client.get("bestDifficulty"))
                st.best_difficulty_ever = st.best_difficulty
                total = 0.0
                for w in client.get("workers", []) or []:
                    if not isinstance(w, dict):
                        continue
                    hr = to_float(w.get("hashRate"))
                    total += hr or 0.0
                    st.workers.append(
                        PoolWorker(
                            name=str(w.get("name", "")),
                            hashrate_hs=hr,
                            best_difficulty=parse_difficulty(w.get("bestDifficulty")),
                            last_seen=_iso_to_ts(w.get("lastSeen")),
                            started=_iso_to_ts(w.get("startTime")),
                        )
                    )
                st.hashrate_hs = total
                seen = [w.last_seen for w in st.workers if w.last_seen]
                st.last_share = max(seen) if seen else None
            out.append(st)
        return out

    async def hashrate_chart(self, address: str) -> list[tuple[float, float]]:
        """The pool's own 10-minute hashrate series for an address (handy to backfill a graph)."""
        data = await self._get(f"/api/client/{address}/chart")
        out: list[tuple[float, float]] = []
        if isinstance(data, list):
            for p in data:
                ts = _iso_to_ts(p.get("label")) if isinstance(p, dict) else None
                v = to_float(p.get("data")) if isinstance(p, dict) else None
                if ts is not None and v is not None:
                    out.append((ts, v))
        return out

    async def test(self) -> ConnectionTest:
        try:
            net = await self._get("/api/network")
            pool = await self._get("/api/pool")
        except SourceError as e:
            return ConnectionTest(
                ok=False,
                message=f"Could not read Public Pool at {self.base}: {e}",
                hints=[
                    "Use the pool's web/API port, not the stratum port. On Umbrel that is usually http://umbrel.local:2019 (stratum is 2018).",
                    "Public Pool needs no password.",
                ],
            )
        if not isinstance(net, dict) or "blocks" not in net:
            return ConnectionTest(ok=False, message="That address answered, but it does not look like Public Pool.")
        miners = pool.get("totalMiners") if isinstance(pool, dict) else None
        return ConnectionTest(
            ok=True,
            message=f"Connected to Public Pool: block {int(net['blocks']):,}, {miners if miners is not None else '?'} miner(s) connected.",
            details={"height": net.get("blocks"), "miners": miners},
        )
