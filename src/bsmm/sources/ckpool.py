"""ckpool solo statistics (solo.ckpool.org, eusolo.ckpool.org, ausolo.ckpool.org or your own ckpool).

``GET {base}/users/{address}`` returns one JSON document per payout address. Hashrates come as
strings with SI suffixes (``"312T"``), which :func:`bsmm.units.parse_si_number` understands.
``GET {base}/pool/pool.status`` returns JSON lines with pool-wide numbers.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar

from bsmm.sources.base import (
    ConnectionTest,
    DataSource,
    PoolStatus,
    PoolWorker,
    SourceBadResponse,
    SourceError,
    fetch_json,
)
from bsmm.units import parse_si_number, to_float, to_int

DEFAULT_URL = "https://solo.ckpool.org"


def parse_user_document(doc: dict[str, Any], address: str, name: str) -> PoolStatus:
    st = PoolStatus(kind="ckpool", name=name, reachable=True, address=address)
    st.hashrate_hs = parse_si_number(doc.get("hashrate1m"))
    st.extra.update(
        {
            "hashrate_5m_hs": parse_si_number(doc.get("hashrate5m")),
            "hashrate_1h_hs": parse_si_number(doc.get("hashrate1hr")),
            "hashrate_1d_hs": parse_si_number(doc.get("hashrate1d")),
            "hashrate_7d_hs": parse_si_number(doc.get("hashrate7d")),
            "workers_connected": to_int(doc.get("workers")),
            "authorised": to_float(doc.get("authorised")),
        }
    )
    st.best_difficulty = to_float(doc.get("bestshare"))
    st.best_difficulty_ever = to_float(doc.get("bestever"))
    st.last_share = to_float(doc.get("lastshare"))
    st.shares = to_float(doc.get("shares"))
    for w in doc.get("worker", []) or []:
        if not isinstance(w, dict):
            continue
        wname = str(w.get("workername", ""))
        st.workers.append(
            PoolWorker(
                name=wname.split(".", 1)[1] if "." in wname else wname,
                hashrate_hs=parse_si_number(w.get("hashrate1m")),
                best_difficulty=to_float(w.get("bestever")) or to_float(w.get("bestshare")),
                last_seen=to_float(w.get("lastshare")),
                shares=to_float(w.get("shares")),
            )
        )
    return st


def parse_pool_status(text: str) -> dict[str, Any]:
    """The pool.status file is several JSON objects, one per line."""
    merged: dict[str, Any] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict):
            merged.update(obj)
    return merged


class CkpoolSource(DataSource):
    kind: ClassVar[str] = "ckpool"
    label: ClassVar[str] = "ckpool solo (solo.ckpool.org or your own)"

    @property
    def base(self) -> str:
        return (self.source.url or DEFAULT_URL).rstrip("/")

    async def pool(self, addresses: list[str]) -> list[PoolStatus]:
        pool_info: dict[str, Any] = {}
        try:
            text = await fetch_json(self.client, f"{self.base}/pool/pool.status", timeout=self.timeout, accept_text=True)
            pool_info = parse_pool_status(str(text))
        except SourceError:
            pass  # per-address stats are what matter
        out: list[PoolStatus] = []
        for addr in addresses:
            try:
                doc = await fetch_json(self.client, f"{self.base}/users/{addr}", timeout=self.timeout)
            except SourceBadResponse as e:
                msg = "no statistics yet for this address (it appears here after its first share)" if "404" in str(e) else str(e)
                out.append(PoolStatus(kind=self.kind, name=self.source.name, reachable=True, address=addr, error=msg))
                continue
            except SourceError as e:
                out.append(PoolStatus(kind=self.kind, name=self.source.name, reachable=False, address=addr, error=str(e)))
                continue
            if not isinstance(doc, dict):
                out.append(PoolStatus(kind=self.kind, name=self.source.name, reachable=True, address=addr, error="unexpected reply"))
                continue
            st = parse_user_document(doc, addr, self.source.name)
            st.pool_hashrate_hs = parse_si_number(pool_info.get("hashrate1m"))
            st.pool_miners = to_int(pool_info.get("Users"))
            out.append(st)
        if not addresses:
            out.append(
                PoolStatus(
                    kind=self.kind,
                    name=self.source.name,
                    reachable=bool(pool_info),
                    pool_hashrate_hs=parse_si_number(pool_info.get("hashrate1m")),
                    pool_miners=to_int(pool_info.get("Users")),
                )
            )
        return out

    async def test(self) -> ConnectionTest:
        try:
            text = await fetch_json(self.client, f"{self.base}/pool/pool.status", timeout=self.timeout, accept_text=True)
        except SourceError as e:
            return ConnectionTest(ok=False, message=f"Could not read {self.base}: {e}", hints=["Default: https://solo.ckpool.org"])
        info = parse_pool_status(str(text))
        if not info:
            return ConnectionTest(ok=False, message="That address answered, but it does not look like a ckpool stats server.")
        return ConnectionTest(
            ok=True,
            message=f"Connected. The pool has {info.get('Users', '?')} users and {info.get('hashrate1m', '?')}H/s.",
            details=info,
        )
