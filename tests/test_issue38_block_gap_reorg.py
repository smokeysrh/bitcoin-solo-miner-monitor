"""Issue #38: block recognition after a long gap, and after a chain reorganisation.

Real ``NetworkService`` and real ``MempoolSpaceSource`` over a fake mempool.space site; no Bitcoin Core.
"""

from __future__ import annotations

from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

from bsmm.engine.network import NetworkService, SourceHealth, _Poller
from bsmm.models import Source
from bsmm.sim.bitcoin_core import OTHER_POOL_ADDR
from bsmm.sources.base import BlockInfo, NetworkSnapshot

WATCHED = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
TIP = 2_000_000
RECENT_LISTED = 15  # mempool.space lists the newest blocks; older heights need a per-height lookup
MARKER = TIP - 30  # a gap older than anything the recent list still shows
OURS = TIP - 20


def _block_json(height: int, paying: dict[int, str]) -> dict[str, Any]:
    address = paying.get(height, OTHER_POOL_ADDR)
    return {
        "id": f"{height:064x}", "height": height, "timestamp": 1_700_000_000 + height * 600, "tx_count": 2000,
        "difficulty": 1.0e14,
        "extras": {"coinbaseAddress": address, "coinbaseAddresses": [address], "reward": 312_500_000,
                   "totalFees": 0, "pool": {"name": "TestPool"}},
    }


def _mempool_site(paying: dict[int, str], *, history: bool = True) -> Starlette:
    """Recent list always works; per-height history only when ``history`` is true."""

    async def handler(request: Request) -> Any:
        path = request.url.path
        not_found = PlainTextResponse("nope", status_code=404)
        try:
            if path == "/api/v1/blocks":
                return JSONResponse([_block_json(h, paying) for h in range(TIP, TIP - RECENT_LISTED, -1)])
            if history and path.startswith("/api/block-height/"):
                height = int(path.rsplit("/", 1)[1])
                return PlainTextResponse(f"{height:064x}") if height <= TIP else not_found
            if history and path.startswith("/api/v1/block/"):
                height = int(path.rsplit("/", 1)[1], 16)
                return JSONResponse(_block_json(height, paying)) if height <= TIP else not_found
        except ValueError:
            return not_found
        return not_found

    return Starlette(routes=[Route("/{p:path}", handler)])


async def _look(net: NetworkService) -> None:
    for poller in net._pollers.values():
        await net._poll(poller)
    await net._merge()


async def _mempool_only_service(lan, paying: dict[int, str], *, history: bool = True) -> NetworkService:
    ctx, hosts = lan
    hosts["mempool.test"] = _mempool_site(paying, history=history)
    net = ctx.network
    net.watch_addresses = lambda: [WATCHED]
    await net.add_source("mempool_space", "mempool", "http://mempool.test", None, None)
    await ctx.store.kv_set("blocks.last_checked", MARKER)
    return net


async def test_gap_older_than_the_recent_list_is_backfilled_without_core(lan):
    ctx, _ = lan
    net = await _mempool_only_service(lan, {OURS: WATCHED})
    await _look(net)
    assert [b["height"] for b in await ctx.store.list_blocks_found()] == [OURS]
    assert await ctx.store.kv_get("blocks.last_checked") == TIP


async def test_gap_that_cannot_be_looked_up_keeps_the_marker(lan):
    ctx, _ = lan
    net = await _mempool_only_service(lan, {OURS: WATCHED}, history=False)
    await _look(net)
    assert await ctx.store.list_blocks_found() == []
    assert await ctx.store.kv_get("blocks.last_checked") == MARKER  # never claims coverage it did not get


def _inject(net: NetworkService, kind: str, snap: NetworkSnapshot) -> None:
    src = Source(id=f"src-{kind}", kind=kind, name=kind)
    health = SourceHealth(id=src.id, kind=kind, name=kind, ok=True)
    net._pollers[src.id] = _Poller(src, impl=None, health=health, snapshot=snap)  # type: ignore[arg-type]


def _snapshot(tip_hash: str, *blocks: BlockInfo) -> NetworkSnapshot:
    return NetworkSnapshot(source="mp", height=blocks[0].height, tip_hash=tip_hash, difficulty=1.0e14,
                           recent_blocks=list(blocks))


def _block(height: int, hash_: str, address: str) -> BlockInfo:
    return BlockInfo(hash=hash_, height=height, ts=float(height), coinbase_addresses=[address])


async def test_same_height_replacement_orphans_a_found_block_but_keeps_its_history(api):
    client, ctx, _ = api
    net = ctx.network
    net.watch_addresses = lambda: [WATCHED]
    await ctx.store.kv_set("blocks.last_checked", 101)
    parent = _block(101, "a101", OTHER_POOL_ADDR)
    _inject(net, "mempool_space", _snapshot("b102", _block(102, "b102", WATCHED), parent))
    await net._merge()
    body = (await client.get("/api/v1/blocks/found")).json()
    assert body["count"] == 1 and body["blocks"][0]["hash"] == "b102"

    _inject(net, "mempool_space", _snapshot("c102", _block(102, "c102", OTHER_POOL_ADDR), parent))
    await net._merge()
    body = (await client.get("/api/v1/blocks/found")).json()
    assert body["count"] == 0 and body["blocks"] == []
    assert [b["hash"] for b in body["orphaned"]] == ["b102"]  # kept as history, no longer counted
    assert len(await ctx.store.list_events(types=["block_orphaned"])) == 1


async def test_same_height_replacement_that_pays_us_is_recognised(api):
    client, ctx, _ = api
    net = ctx.network
    net.watch_addresses = lambda: [WATCHED]
    await ctx.store.kv_set("blocks.last_checked", 101)
    parent = _block(101, "a101", OTHER_POOL_ADDR)
    _inject(net, "mempool_space", _snapshot("b102", _block(102, "b102", OTHER_POOL_ADDR), parent))
    await net._merge()
    assert (await client.get("/api/v1/blocks/found")).json()["count"] == 0

    _inject(net, "mempool_space", _snapshot("c102", _block(102, "c102", WATCHED), parent))
    await net._merge()
    body = (await client.get("/api/v1/blocks/found")).json()
    assert [b["hash"] for b in body["blocks"]] == ["c102"] and body["orphaned"] == []


async def test_two_sources_disagreeing_about_a_height_leave_one_recent_block(lan):
    ctx, _ = lan
    net = ctx.network
    _inject(net, "bitcoin_core", NetworkSnapshot(source="core", height=102, difficulty=1.0e14,
                                                 recent_blocks=[_block(102, "core102", OTHER_POOL_ADDR)]))
    _inject(net, "mempool_space", NetworkSnapshot(source="mp", height=102, difficulty=1.0e14,
                                                  recent_blocks=[_block(102, "mp102", OTHER_POOL_ADDR)]))
    await net._merge()
    assert [(b.height, b.hash) for b in net.state.recent_blocks] == [(102, "core102")]
