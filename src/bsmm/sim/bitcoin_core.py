"""A tiny fake Bitcoin Core JSON-RPC server (read-only subset) with a chain you can extend.

Lets tests and demos exercise node monitoring and "block found" detection without a real node.
Field names follow Bitcoin Core 29.
"""

from __future__ import annotations

import base64
import hashlib
import time
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

OTHER_POOL_ADDR = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"


class FakeBitcoinCore:
    def __init__(self, *, height: int = 972_174, difficulty: float = 140_577_680_051_919.6, user: str = "umbrel",
                 password: str = "secret", chain: str = "main") -> None:
        self.user = user
        self.password = password
        self.chain = chain
        self.difficulty = difficulty
        self.headers_ahead = 0
        self.ibd = False
        self.warming_up = False
        self.started = time.time()
        self.blocks: list[dict[str, Any]] = []
        self.txs: dict[str, dict[str, Any]] = {}
        base_time = time.time() - height % 2016 * 600
        self._genesis_offset = height  # heights below are synthetic
        self.base_height = height - 2100
        for h in range(self.base_height, height + 1):
            self._add(h, base_time - (height - h) * 600, OTHER_POOL_ADDR, 312_500_000, "/FakePool/")
        self.calls: list[str] = []

    # -- chain ---------------------------------------------------------------------------------

    def _add(self, height: int, ts: float, address: str, sats: int, tag: str) -> dict[str, Any]:
        bhash = hashlib.sha256(f"block{height}".encode()).hexdigest()
        txid = hashlib.sha256(f"cb{height}{address}".encode()).hexdigest()
        coinbase_hex = (b"\x03" + height.to_bytes(3, "little") + tag.encode()).hex()
        self.txs[txid] = {
            "txid": txid,
            "vin": [{"coinbase": coinbase_hex, "sequence": 4294967295}],
            "vout": [{"value": sats / 1e8, "n": 0, "scriptPubKey": {"address": address, "type": "witness_v0_keyhash"}}],
        }
        blk = {"hash": bhash, "height": height, "time": int(ts), "mediantime": int(ts) - 300, "nTx": 2000, "tx": [txid, "ab" * 32]}
        self.blocks.append(blk)
        return blk

    @property
    def height(self) -> int:
        return int(self.blocks[-1]["height"])

    def mine_block(self, address: str = OTHER_POOL_ADDR, sats: int = 312_500_000, tag: str = "/FakePool/") -> dict[str, Any]:
        return self._add(self.height + 1, time.time(), address, sats, tag)

    def _by_hash(self, h: str) -> dict[str, Any]:
        for blk in reversed(self.blocks):
            if blk["hash"] == h:
                found: dict[str, Any] = blk
                return found
        raise _Rpc(-5, "Block not found")

    def _by_height(self, n: int) -> dict[str, Any]:
        i = n - self.base_height
        if i < 0 or i >= len(self.blocks):
            raise _Rpc(-8, "Block height out of range")
        return self.blocks[i]

    # -- rpc -----------------------------------------------------------------------------------

    def handle(self, method: str, params: list[Any]) -> Any:
        self.calls.append(method)
        if self.warming_up:
            raise _Rpc(-28, "Loading block index...")
        tip = self.blocks[-1]
        if method == "getblockchaininfo":
            return {
                "chain": self.chain, "blocks": self.height, "headers": self.height + self.headers_ahead,
                "bestblockhash": tip["hash"], "difficulty": self.difficulty, "time": tip["time"], "mediantime": tip["mediantime"],
                "verificationprogress": 0.3 if self.ibd else 0.99999, "initialblockdownload": self.ibd,
                "size_on_disk": 780_000_000_000, "pruned": False, "warnings": [],
            }
        if method == "getnetworkinfo":
            return {"version": 290000, "subversion": "/Satoshi:29.0.0/", "protocolversion": 70016, "connections": 18,
                    "connections_in": 6, "connections_out": 12, "networkactive": True, "relayfee": 1e-05, "warnings": []}
        if method == "getmininginfo":
            return {"blocks": self.height, "difficulty": self.difficulty, "networkhashps": 1.0e21, "pooledtx": 4200, "chain": self.chain, "warnings": []}
        if method == "getmempoolinfo":
            return {"loaded": True, "size": 4200, "bytes": 2_100_000, "usage": 9_000_000, "maxmempool": 300_000_000, "mempoolminfee": 1e-05, "minrelaytxfee": 1e-05}
        if method == "uptime":
            return int(time.time() - self.started) + 86_400
        if method == "getblockhash":
            return self._by_height(int(params[0]))["hash"]
        if method == "getblockheader":
            b = self._by_hash(params[0])
            return {"hash": b["hash"], "height": b["height"], "time": b["time"], "mediantime": b["mediantime"]}
        if method == "getblock":
            b = self._by_hash(params[0])
            return dict(b)
        if method == "getrawtransaction":
            tx = self.txs.get(params[0])
            if not tx:
                raise _Rpc(-5, "No such transaction")
            return tx
        if method in {"getbestblockhash"}:
            return tip["hash"]
        if method == "getblockcount":
            return self.height
        if method == "getdifficulty":
            return self.difficulty
        raise _Rpc(-32601, f"Method not found: {method}")

    def app(self) -> Starlette:
        sim = self

        def auth_ok(request: Request) -> bool:
            header = request.headers.get("authorization", "")
            if not header.startswith("Basic "):
                return False
            try:
                user, _, pw = base64.b64decode(header[6:]).decode().partition(":")
            except Exception:
                return False
            return user == sim.user and pw == sim.password

        def run_one(item: dict[str, Any]) -> dict[str, Any]:
            try:
                return {"result": sim.handle(item["method"], item.get("params", [])), "error": None, "id": item.get("id")}
            except _Rpc as e:
                return {"result": None, "error": {"code": e.code, "message": e.message}, "id": item.get("id")}

        async def rpc(request: Request) -> JSONResponse | PlainTextResponse:
            if not auth_ok(request):
                return PlainTextResponse("", status_code=401)
            body = await request.json()
            if isinstance(body, list):
                return JSONResponse([run_one(i) for i in body])
            out = run_one(body)
            return JSONResponse(out, status_code=500 if out["error"] else 200)

        return Starlette(routes=[Route("/", rpc, methods=["POST"])])


class _Rpc(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
