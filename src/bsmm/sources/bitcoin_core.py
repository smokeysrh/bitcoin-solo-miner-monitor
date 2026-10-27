"""Bitcoin Core over JSON-RPC (read-only).

Only a short allow-list of *read-only chain/network* methods can be called through this client, so
the app can never touch a wallet or send a transaction even if told to. Block notifications are
done by polling ``getblockchaininfo`` every few seconds (cheap, no extra native dependency); a new
tip then triggers a coinbase check, which is how a block you found is recognised.
"""

from __future__ import annotations

import base64
import re
import time
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import urlsplit

import httpx

from bsmm.net import local_address_towards
from bsmm.sources.base import (
    BlockInfo,
    ConnectionTest,
    DataSource,
    NetworkSnapshot,
    NodeStatus,
    SourceAuthError,
    SourceBadResponse,
    SourceError,
    SourceForbidden,
    SourceUnreachable,
)
from bsmm.units import to_float, to_int

ALLOWED_METHODS = frozenset(
    {
        "getblockchaininfo",
        "getnetworkinfo",
        "getmininginfo",
        "getmempoolinfo",
        "getbestblockhash",
        "getblockcount",
        "getblockhash",
        "getblockheader",
        "getblock",
        "getblockstats",
        "getrawtransaction",
        "getdifficulty",
        "getnetworkhashps",
        "getconnectioncount",
        "getnettotals",
        "uptime",
        "estimatesmartfee",
    }
)
DEFAULT_PORT = 8332
_PRINTABLE_RUN = re.compile(rb"[\x20-\x7e]{4,}")


class RpcError(SourceError):
    code = "rpc_error"

    def __init__(self, message: str, rpc_code: int | None = None) -> None:
        super().__init__(message)
        self.rpc_code = rpc_code


def normalise_url(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        raise ValueError("enter the node's address, for example http://192.168.1.10:8332")
    if "://" not in text:
        text = "http://" + text
    m = re.match(r"^(?P<scheme>https?)://(?P<host>[^/:]+|\[[^\]]+\])(?::(?P<port>\d+))?", text)
    if not m:
        raise ValueError(f"{raw!r} is not a valid address")
    port = m.group("port") or str(DEFAULT_PORT)
    return f"{m.group('scheme')}://{m.group('host')}:{port}"


class BitcoinRPC:
    def __init__(self, url: str, client: httpx.AsyncClient, *, user: str | None, password: str | None,
                 cookie_path: str | None = None, timeout: float = 8.0) -> None:
        self.url = normalise_url(url)
        self.client = client
        self.user = user
        self.password = password
        self.cookie_path = cookie_path
        self.timeout = timeout
        self._id = 0

    def _auth_header(self) -> dict[str, str]:
        user, password = self.user, self.password
        if self.cookie_path:
            try:
                text = Path(self.cookie_path).expanduser().read_text().strip()
            except OSError as e:
                raise SourceAuthError(f"cannot read the RPC cookie file ({e.__class__.__name__})") from e
            user, _, password = text.partition(":")
        if not user:
            raise SourceAuthError("an RPC user name and password (or cookie file) is required")
        raw = f"{user}:{password or ''}".encode()
        return {"Authorization": "Basic " + base64.b64encode(raw).decode(), "Content-Type": "application/json"}

    async def _post(self, payload: Any) -> Any:
        for item in payload if isinstance(payload, list) else [payload]:
            if item["method"] not in ALLOWED_METHODS:
                raise RpcError(f"RPC method {item['method']!r} is not allowed (read-only client)")
        try:
            resp = await self.client.post(self.url, json=payload, headers=self._auth_header(), timeout=self.timeout)
        except httpx.TimeoutException as e:
            raise SourceUnreachable(f"timed out after {self.timeout:g}s") from e
        except httpx.TransportError as e:
            msg = str(e).lower()
            raise SourceUnreachable("connection refused" if "refused" in msg else (str(e) or "connection failed")[:120]) from e
        if resp.status_code == 401:
            raise SourceAuthError("wrong RPC user name or password")
        if resp.status_code == 403:
            raise SourceForbidden("the node refused this computer (rpcallowip)")
        if resp.status_code == 404:
            raise SourceBadResponse("HTTP 404: this is not a Bitcoin Core RPC endpoint")
        try:
            return resp.json()
        except ValueError as e:
            raise SourceBadResponse(f"HTTP {resp.status_code}: reply was not JSON") from e

    async def call(self, method: str, params: list[Any] | None = None) -> Any:
        self._id += 1
        body = await self._post({"jsonrpc": "1.0", "id": self._id, "method": method, "params": params or []})
        if not isinstance(body, dict):
            raise SourceBadResponse("unexpected RPC reply")
        err = body.get("error")
        if err:
            raise RpcError(str(err.get("message", err)), to_int(err.get("code")))
        return body.get("result")

    async def batch(self, calls: list[tuple[str, list[Any]]]) -> list[Any]:
        """One HTTP request, many calls. Failed calls come back as :class:`RpcError` instances."""
        payload = []
        for method, params in calls:
            self._id += 1
            payload.append({"jsonrpc": "1.0", "id": self._id, "method": method, "params": params})
        body = await self._post(payload)
        if not isinstance(body, list):
            raise SourceBadResponse("unexpected RPC batch reply")
        by_id = {item.get("id"): item for item in body if isinstance(item, dict)}
        results: list[Any] = []
        for item in payload:
            reply = by_id.get(item["id"], {})
            if reply.get("error"):
                err = reply["error"]
                results.append(RpcError(str(err.get("message", err)), to_int(err.get("code"))))
            else:
                results.append(reply.get("result"))
        return results


def coinbase_tag(coinbase_hex: str | None) -> str | None:
    """Best-effort pool tag from the coinbase scriptSig (the longest readable text in it)."""
    if not coinbase_hex:
        return None
    try:
        raw = bytes.fromhex(coinbase_hex)
    except ValueError:
        return None
    runs = _PRINTABLE_RUN.findall(raw)
    if not runs:
        return None
    best = max(runs, key=len).decode("ascii", "replace").strip("/ \t")
    return best[:48] or None


class BitcoinCoreSource(DataSource):
    kind: ClassVar[str] = "bitcoin_core"
    label: ClassVar[str] = "Bitcoin Core node (RPC)"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._rpc: BitcoinRPC | None = None
        self._epoch_cache: dict[int, float] = {}
        self._block_cache: dict[str, BlockInfo] = {}
        self._last_status: NodeStatus | None = None

    @property
    def rpc(self) -> BitcoinRPC:
        if self._rpc is None:
            self._rpc = BitcoinRPC(
                self.source.url or "",
                self.client,
                user=self.secret.get("rpc_user") or self.source.options.get("rpc_user"),
                password=self.secret.get("rpc_password"),
                cookie_path=self.source.options.get("cookie_path"),
                timeout=self.timeout,
            )
        return self._rpc

    # -- node health ----------------------------------------------------------------------------

    async def _fetch_core(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], int | None]:
        results = await self.rpc.batch(
            [("getblockchaininfo", []), ("getnetworkinfo", []), ("getmininginfo", []), ("getmempoolinfo", []), ("uptime", [])]
        )
        chain, net, mining, mempool, uptime = results
        for r in (chain, net):
            if isinstance(r, RpcError):
                raise r
        mining = mining if isinstance(mining, dict) else {}
        mempool = mempool if isinstance(mempool, dict) else {}
        return chain, net, mining, mempool, (uptime if isinstance(uptime, int) else None)

    async def node(self) -> NodeStatus | None:
        try:
            chain, net, mining, mempool, uptime = await self._fetch_core()
        except RpcError as e:
            msg = f"node says: {e}"
            if e.rpc_code == -28:
                msg = "the node is still starting up (loading the block index)"
            st = NodeStatus(reachable=True, error=msg)
            self._last_status = st
            return st
        except SourceError as e:
            st = NodeStatus(reachable=False, error=str(e))
            self._last_status = st
            return st
        warnings: list[str] = []
        for w in (chain.get("warnings"), net.get("warnings")):
            if isinstance(w, str) and w:
                warnings.append(w)
            elif isinstance(w, list):
                warnings.extend(str(x) for x in w if x)
        version = net.get("version")
        st = NodeStatus(
            reachable=True,
            version=_format_version(version) if isinstance(version, int) else None,
            subversion=net.get("subversion"),
            chain=chain.get("chain"),
            blocks=to_int(chain.get("blocks")),
            headers=to_int(chain.get("headers")),
            initial_block_download=bool(chain.get("initialblockdownload")),
            verification_progress=to_float(chain.get("verificationprogress")),
            connections=to_int(net.get("connections")),
            connections_in=to_int(net.get("connections_in")),
            connections_out=to_int(net.get("connections_out")),
            mempool_tx_count=to_int(mempool.get("size")),
            mempool_bytes=to_int(mempool.get("bytes")),
            mempool_max_bytes=to_int(mempool.get("maxmempool")),
            min_relay_fee_sat_vb=(to_float(net.get("relayfee")) or 0.0) * 1e8 / 1000 or None,
            size_on_disk=to_int(chain.get("size_on_disk")),
            pruned=bool(chain.get("pruned")),
            uptime_s=uptime,
            network_active=bool(net.get("networkactive", True)),
            best_block_hash=chain.get("bestblockhash"),
            difficulty=to_float(chain.get("difficulty")),
            network_hashrate_hs=to_float(mining.get("networkhashps")),
            warnings=warnings,
        )
        self._last_status = st
        return st

    # -- chain data -----------------------------------------------------------------------------

    async def _epoch_start_time(self, height: int) -> float | None:
        start = height - (height % 2016)
        if start in self._epoch_cache:
            return self._epoch_cache[start]
        try:
            h = await self.rpc.call("getblockhash", [start])
            hdr = await self.rpc.call("getblockheader", [h])
        except SourceError:
            return None
        self._epoch_cache = {start: float(hdr["time"])}  # only the current epoch is ever needed
        return self._epoch_cache[start]

    async def block_info(self, height: int) -> BlockInfo | None:
        """Summary of one block incl. coinbase payout addresses (2-3 RPC calls, cached by hash)."""
        try:
            bhash = await self.rpc.call("getblockhash", [height])
            if bhash in self._block_cache:
                return self._block_cache[bhash]
            blk = await self.rpc.call("getblock", [bhash, 1])
            cb_txid = blk["tx"][0]
            cb = await self.rpc.call("getrawtransaction", [cb_txid, True, bhash])
        except (SourceError, KeyError, IndexError, TypeError):
            return None
        addrs: list[str] = []
        total = 0
        for vout in cb.get("vout", []):
            total += round(float(vout.get("value", 0)) * 1e8)
            spk = vout.get("scriptPubKey", {})
            addr = spk.get("address") or (spk.get("addresses") or [None])[0]
            if addr:
                addrs.append(addr)
        coinbase_hex = (cb.get("vin") or [{}])[0].get("coinbase")
        info = BlockInfo(
            hash=bhash,
            height=height,
            ts=float(blk.get("time", 0)),
            tx_count=to_int(blk.get("nTx")) or len(blk.get("tx", [])),
            pool_name=coinbase_tag(coinbase_hex),
            reward_sats=total,
            coinbase_addresses=addrs,
        )
        self._block_cache[bhash] = info
        if len(self._block_cache) > 200:
            for k in list(self._block_cache)[:50]:
                self._block_cache.pop(k, None)
        return info

    async def network(self) -> NetworkSnapshot | None:
        try:
            chain, _net, mining, mempool, _up = await self._fetch_core()
        except SourceError:
            return None
        height = to_int(chain.get("blocks")) or 0
        tip_hash = chain.get("bestblockhash")
        snap = NetworkSnapshot(
            source=f"bitcoin_core:{self.source.name}",
            height=height,
            tip_hash=tip_hash,
            tip_time=to_float(chain.get("time")),
            difficulty=to_float(chain.get("difficulty")),
            network_hashrate_hs=to_float(mining.get("networkhashps")),
            mempool_tx_count=to_int(mempool.get("size")),
            mempool_vsize=to_int(mempool.get("bytes")),
        )
        if chain.get("initialblockdownload"):
            snap.warnings.append("The node is still syncing; network figures may be behind.")
        snap.epoch_start_time = await self._epoch_start_time(height)
        blocks: list[BlockInfo] = []
        for h in range(height, max(0, height - 5), -1):
            b = await self.block_info(h)
            if b:
                blocks.append(b)
        snap.recent_blocks = blocks
        return snap

    async def test(self) -> ConnectionTest:
        try:
            chain, net, _mining, _mempool, _up = await self._fetch_core()
        except SourceForbidden:
            host = str(urlsplit(str(self.source.url)).hostname or "")
            me = local_address_towards(host) if host else None
            subnet = f"{me.rsplit('.', 1)[0]}.0/24" if me and me.count(".") == 3 else "your network, e.g. 192.168.1.0/24"
            return ConnectionTest(
                ok=False,
                message=f"The node refused this computer{f' ({me})' if me else ''} before it even looked at the login. "
                        "This is the node's allow-list (rpcallowip), not your user name or password.",
                hints=[
                    f"Add rpcallowip={subnet} to the node's bitcoin.conf (on Umbrel, look in the Bitcoin Node app's advanced settings; elsewhere edit bitcoin.conf) and restart the node.",
                    "Your user name and password can only be checked once the node accepts this computer.",
                    "No need for the node's RPC at all? Public Pool or mempool.space already supply block height, fees and difficulty.",
                ],
            )
        except SourceAuthError as e:
            return ConnectionTest(
                ok=False,
                message=f"The node rejected the login: {e}",
                hints=[
                    "Umbrel: open the Bitcoin Node app, choose Connect, then RPC; it lists the user name and password.",
                    "Start9 / RaspiBlitz / myNode: the RPC user and password are shown in the node's own Connect or Credentials page.",
                    "Running Bitcoin Core yourself on this computer? Use the cookie file instead (Advanced: cookie path).",
                ],
            )
        except RpcError as e:
            hint = ["Wait a minute and test again."] if e.rpc_code == -28 else []
            return ConnectionTest(ok=False, message=f"The node answered with an error: {e}", hints=hint)
        except SourceError as e:
            return ConnectionTest(
                ok=False,
                message=f"Could not reach the node: {e}",
                hints=[
                    "Check the address and that RPC port 8332 is reachable from this computer.",
                    "In bitcoin.conf you need server=1 and an rpcallowip line that covers this computer's network.",
                ],
            )
        except ValueError as e:
            return ConnectionTest(ok=False, message=str(e))
        blocks = to_int(chain.get("blocks")) or 0
        headers = to_int(chain.get("headers")) or blocks
        syncing = bool(chain.get("initialblockdownload")) or headers - blocks > 2
        sub = net.get("subversion") or ""
        msg = f"Connected to {sub or 'Bitcoin Core'} on {chain.get('chain')}: block {blocks:,}"
        msg += " (still syncing)." if syncing else " (fully synced)."
        return ConnectionTest(
            ok=True,
            message=msg,
            details={"chain": chain.get("chain"), "blocks": blocks, "headers": headers, "syncing": syncing, "subversion": sub},
        )


def _format_version(v: int) -> str:
    """290000 -> 29.0.0"""
    major, rest = divmod(v, 10000)
    minor, patch = divmod(rest, 100)
    return f"{major}.{minor}.{patch}"


def now() -> float:  # tiny seam so tests can freeze time
    return time.time()
