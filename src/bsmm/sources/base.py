"""Data sources: Bitcoin node, mining pools and public chain APIs, behind one small interface."""

from __future__ import annotations

import json
import re
import time
from abc import ABC
from typing import Any, ClassVar

import httpx
from pydantic import BaseModel, ConfigDict, Field

from bsmm.models import Source


class SourceError(Exception):
    code = "source_error"


class SourceUnreachable(SourceError):
    code = "unreachable"


class SourceAuthError(SourceError):
    code = "auth_failed"


class SourceForbidden(SourceAuthError):
    """The server answered 403: it refuses this computer, whatever login is sent."""
    code = "forbidden"
class SourceBadResponse(SourceError):
    code = "bad_response"


class _M(BaseModel):
    model_config = ConfigDict(extra="ignore")


class BlockInfo(_M):
    hash: str
    height: int
    ts: float
    tx_count: int | None = None
    pool_name: str | None = None
    reward_sats: int | None = None
    fees_sats: int | None = None
    coinbase_addresses: list[str] = Field(default_factory=list)


class NetworkSnapshot(_M):
    """What we know about the Bitcoin network right now, from the best available source."""

    source: str
    ts: float = Field(default_factory=time.time)
    height: int | None = None
    tip_hash: str | None = None
    tip_time: float | None = None
    difficulty: float | None = None
    network_hashrate_hs: float | None = None
    epoch_start_time: float | None = None
    #: provider's own estimate for the next retarget, if it publishes one (mempool.space)
    est_difficulty_change_pct: float | None = None
    est_retarget_ts: float | None = None
    mempool_tx_count: int | None = None
    mempool_vsize: int | None = None
    fees_sat_vb: dict[str, float] | None = None
    prices: dict[str, float] | None = None
    recent_blocks: list[BlockInfo] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class NodeStatus(_M):
    kind: str = "bitcoin_core"
    reachable: bool = False
    error: str | None = None
    version: str | None = None
    subversion: str | None = None
    chain: str | None = None
    blocks: int | None = None
    headers: int | None = None
    initial_block_download: bool | None = None
    verification_progress: float | None = None
    connections: int | None = None
    connections_in: int | None = None
    connections_out: int | None = None
    mempool_tx_count: int | None = None
    mempool_bytes: int | None = None
    mempool_max_bytes: int | None = None
    min_relay_fee_sat_vb: float | None = None
    size_on_disk: int | None = None
    pruned: bool | None = None
    uptime_s: int | None = None
    network_active: bool | None = None
    best_block_hash: str | None = None
    difficulty: float | None = None
    network_hashrate_hs: float | None = None
    warnings: list[str] = Field(default_factory=list)
    checked_at: float = Field(default_factory=time.time)

    @property
    def synced(self) -> bool:
        if self.initial_block_download:
            return False
        if self.blocks is not None and self.headers is not None and self.headers - self.blocks > 2:
            return False
        return bool(self.reachable)


class PoolWorker(_M):
    name: str
    hashrate_hs: float | None = None
    best_difficulty: float | None = None
    last_seen: float | None = None
    started: float | None = None
    shares: float | None = None


class PoolStatus(_M):
    kind: str
    name: str
    reachable: bool = False
    error: str | None = None
    pool_hashrate_hs: float | None = None
    pool_miners: int | None = None
    blocks_found: int | None = None
    blocks: list[dict[str, Any]] = Field(default_factory=list)
    #: stats for the configured payout address(es)
    address: str | None = None
    hashrate_hs: float | None = None
    best_difficulty: float | None = None
    best_difficulty_ever: float | None = None
    workers: list[PoolWorker] = Field(default_factory=list)
    last_share: float | None = None
    shares: float | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
    checked_at: float = Field(default_factory=time.time)


class ConnectionTest(_M):
    ok: bool
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    hints: list[str] = Field(default_factory=list)


class DataSource(ABC):
    kind: ClassVar[str]
    label: ClassVar[str]

    def __init__(self, source: Source, secret: dict[str, str], client: httpx.AsyncClient, *, timeout: float = 8.0) -> None:
        self.source = source
        self.secret = secret
        self.client = client
        self.timeout = timeout

    async def network(self) -> NetworkSnapshot | None:
        return None

    async def node(self) -> NodeStatus | None:
        return None

    async def pool(self, addresses: list[str]) -> list[PoolStatus]:
        return []

    async def test(self) -> ConnectionTest:
        return ConnectionTest(ok=False, message="not implemented")


_LOOSE = re.compile(r"[^\x20-\x7e]")


async def fetch_json(
    client: httpx.AsyncClient,
    url: str,
    *,
    timeout: float,
    method: str = "GET",
    json_body: Any = None,
    auth: tuple[str, str] | None = None,
    headers: dict[str, str] | None = None,
    accept_text: bool = False,
) -> Any:
    try:
        resp = await client.request(method, url, json=json_body, auth=auth, headers=headers, timeout=timeout)
    except httpx.TimeoutException as e:
        raise SourceUnreachable(f"timed out after {timeout:g}s") from e
    except httpx.TransportError as e:
        raise SourceUnreachable(_describe(e)) from e
    if resp.status_code == 401:
        raise SourceAuthError("authentication failed (wrong user or password)")
    if resp.status_code == 403:
        raise SourceAuthError("access forbidden (is this machine allowed by rpcallowip / the proxy?)")
    if resp.status_code >= 400 and not (resp.status_code == 500 and "json" in resp.headers.get("content-type", "")):
        raise SourceBadResponse(f"HTTP {resp.status_code}")
    if accept_text:
        return resp.text
    try:
        return resp.json()
    except (ValueError, json.JSONDecodeError) as e:
        raise SourceBadResponse("the server did not return JSON") from e


def _describe(e: Exception) -> str:
    text = str(e).lower()
    if "refused" in text:
        return "connection refused"
    if "name or service" in text or "getaddrinfo" in text or "nodename" in text:
        return "host name not found"
    if "no route" in text or "unreachable" in text:
        return "no route to host"
    return (str(e) or e.__class__.__name__)[:120]
