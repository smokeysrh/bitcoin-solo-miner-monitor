"""Bitcoin network, your node and pool, solo-mining odds and blocks."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from bsmm.api.deps import get_ctx, require
from bsmm.api.errors import ApiError, bad_request, not_found
from bsmm.auth import Principal
from bsmm.context import AppContext
from bsmm.engine.network import PUBLIC_SOURCE_ID, SOURCE_CLASSES
from bsmm.engine.odds import build_odds
from bsmm.models import Source
from bsmm.sources.base import ConnectionTest

router = APIRouter()


@router.get("/network", tags=["bitcoin"], operation_id="getNetwork",
            summary="Bitcoin network state: block height, difficulty, hashrate, halving, difficulty adjustment, fees, price",
            description="Merged from your node, your pool and mempool.space, in that order of preference. `source` says which one answered.")
async def network(ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("read"))) -> dict[str, Any]:
    return ctx.network.state.model_dump(mode="json", exclude={"pools"})


@router.get("/node", tags=["bitcoin"], operation_id="getNode", summary="Your Bitcoin node: sync, peers, mempool, version")
async def node(ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("read"))) -> dict[str, Any]:
    n = ctx.network.state.node
    return {"configured": n is not None, "node": n.model_dump(mode="json") if n else None, "behind_by": ctx.network.state.node_behind_by}


@router.get("/pool", tags=["bitcoin"], operation_id="getPool", summary="Your pool's view of your workers and best shares")
async def pool(ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("read"))) -> dict[str, Any]:
    return {"pools": [p.model_dump(mode="json") for p in ctx.network.state.pools]}


@router.get("/blocks/recent", tags=["bitcoin"], operation_id="getRecentBlocks", summary="The latest blocks on the chain")
async def recent_blocks(ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("read"))) -> dict[str, Any]:
    mine = {b["hash"] for b in await ctx.store.list_blocks_found()}
    return {"blocks": [{**b.model_dump(mode="json"), "yours": b.hash in mine} for b in ctx.network.state.recent_blocks]}


@router.get("/blocks/found", tags=["bitcoin"], operation_id="getBlocksFound", summary="Blocks that paid one of your addresses (hopefully a long list)")
async def blocks_found(ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("read"))) -> dict[str, Any]:
    blocks = await ctx.store.list_blocks_found()
    return {"count": len(blocks), "total_reward_sats": sum(b.get("reward_sats") or 0 for b in blocks), "blocks": blocks}


@router.get(
    "/odds",
    tags=["bitcoin"],
    operation_id="getOdds",
    summary="Your chance of finding a block, expected cost, and 'what if' calculations",
    description="With no parameters it uses your live fleet hashrate and the current difficulty. Add `hashrate_ths` and/or `difficulty` "
    "to ask 'what if I had 50 TH/s?' or 'what if difficulty doubles?'. `growth` models the network growing by that fraction per year "
    "(0.3 = 30%).",
)
async def odds(
    hashrate_ths: float | None = Query(None, ge=0, description="Hashrate in TH/s to use instead of your fleet's"),
    difficulty: float | None = Query(None, gt=0),
    power_w: float | None = Query(None, ge=0, description="Power draw in watts to cost against"),
    growth: float | None = Query(None, ge=-0.9, le=10),
    ctx: AppContext = Depends(get_ctx),
    _: Principal = Depends(require("read")),
) -> dict[str, Any]:
    summary = ctx.fleet.summary(fresh=True)
    work_hashes, work_blocks = ctx.fleet.work
    found = await ctx.store.list_blocks_found()
    return build_odds(
        summary, ctx.network.state, ctx.settings.current, work_hashes=work_hashes, expected_blocks_of_work=work_blocks,
        blocks_found=len(found), hashrate_hs=None if hashrate_ths is None else hashrate_ths * 1e12, difficulty=difficulty,
        power_w=power_w, growth=growth,
    )


# ------------------------------------------------------------------------------------------ sources


class SourceBody(BaseModel):
    kind: str = Field(description="bitcoin_core | public_pool | ckpool | mempool_space")
    name: str | None = Field(None, max_length=60)
    url: str | None = Field(None, max_length=300)
    secret: dict[str, str] = Field(default_factory=dict, description="Write-only. bitcoin_core: {rpc_user, rpc_password}")
    options: dict[str, Any] = Field(default_factory=dict, description="bitcoin_core: {cookie_path}")
    enabled: bool = True


class SourcePatch(BaseModel):
    name: str | None = None
    url: str | None = None
    secret: dict[str, str] | None = Field(None, description="Send to replace; omit to keep the stored secret; {} to clear")
    options: dict[str, Any] | None = None
    enabled: bool | None = None


SOURCE_HELP: dict[str, dict[str, Any]] = {
    "bitcoin_core": {
        "title": "Bitcoin Core node (RPC)",
        "url_example": "http://umbrel.local:8332",
        "secret_fields": [{"name": "rpc_user", "label": "RPC user name"}, {"name": "rpc_password", "label": "RPC password", "secret": True}],
        "option_fields": [{"name": "cookie_path", "label": "Cookie file (alternative to user/password, same computer only)"}],
        "gives": ["sync status", "peers", "mempool", "your own difficulty and height", "recognising a block you find"],
        "where_to_find_login": "Umbrel: Bitcoin Node app > Connect > RPC. Start9/RaspiBlitz/myNode: the node's Connect or Credentials page.",
    },
    "public_pool": {
        "title": "Public Pool (Umbrel / Start9 / self-hosted solo pool)",
        "url_example": "http://umbrel.local:2019",
        "secret_fields": [],
        "gives": ["network height and difficulty", "your workers' pool-side hashrate", "best shares", "blocks found by the pool"],
        "where_to_find_login": "No login. Use the pool's web/API port (Umbrel: 2019), not the stratum port (2018).",
    },
    "ckpool": {
        "title": "ckpool solo (solo.ckpool.org or your own)",
        "url_example": "https://solo.ckpool.org",
        "secret_fields": [],
        "gives": ["pool-side hashrate per worker", "best share ever", "last share time"],
        "where_to_find_login": "No login. Your payout address is the account; stats appear after your first share.",
    },
    "mempool_space": {
        "title": "mempool.space or your own mempool",
        "url_example": "https://mempool.space  or  http://umbrel.local:3006",
        "secret_fields": [],
        "gives": ["difficulty, height, halving, difficulty adjustment estimate", "fees", "BTC price", "recent blocks"],
        "where_to_find_login": "No login.",
    },
}


def _public(src: Source) -> dict[str, Any]:
    return src.model_dump(mode="json")


@router.get("/sources/kinds", tags=["sources"], operation_id="listSourceKinds", summary="The kinds of node/pool/data sources you can add, with what each needs")
async def source_kinds(_: Principal = Depends(require("read"))) -> dict[str, Any]:
    return {"kinds": [{"kind": k, "label": SOURCE_CLASSES[k].label, **SOURCE_HELP.get(k, {})} for k in SOURCE_CLASSES if k != "demo"]}


@router.get("/sources", tags=["sources"], operation_id="listSources", summary="Configured nodes, pools and data sources with their health")
async def list_sources(ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("read"))) -> dict[str, Any]:
    health = {h.id: h for h in ctx.network.state.sources}
    items = []
    for s in await ctx.store.list_sources():
        h = health.get(s.id)
        items.append({**_public(s), "health": h.model_dump(mode="json") if h else None})
    implicit = [{"id": h.id, "kind": h.kind, "name": h.name, "implicit": True, "health": h.model_dump(mode="json")} for h in ctx.network.state.sources if h.implicit]
    return {"sources": items, "implicit": implicit}


@router.post("/sources/test", tags=["sources"], operation_id="testSource", summary="Try a source without saving it (the wizard's Test button)")
async def test_source(body: SourceBody, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("admin"))) -> ConnectionTest:
    return await ctx.network.test_source(body.kind, body.url, body.secret, body.options)


@router.post("/sources", tags=["sources"], operation_id="addSource", summary="Add a node, pool or data source (admin)",
             description="The connection is tested first and the source is saved only if it works, unless `?force=true`.")
async def add_source(body: SourceBody, force: bool = False, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("admin"))) -> dict[str, Any]:
    if body.kind not in SOURCE_CLASSES or body.kind == "demo":
        raise bad_request(f"Unknown source type {body.kind!r}.", "Valid: " + ", ".join(k for k in SOURCE_CLASSES if k != "demo"))
    result = await ctx.network.test_source(body.kind, body.url, body.secret, body.options)
    if not result.ok and not force:
        raise ApiError(422, "connection_failed", result.message, " ".join(result.hints) or None, result.model_dump())
    src = await ctx.network.add_source(body.kind, body.name or "", body.url, body.secret, body.options)
    return {"source": _public(src), "test": result.model_dump()}


@router.patch("/sources/{source_id}", tags=["sources"], operation_id="updateSource", summary="Edit a source (admin)")
async def update_source(source_id: str, body: SourcePatch, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("admin"))) -> dict[str, Any]:
    src = await ctx.store.get_source(source_id)
    if src is None:
        raise not_found("That source")
    data = body.model_dump(exclude_unset=True)
    for k in ("name", "url", "options", "enabled"):
        if k in data and data[k] is not None:
            setattr(src, k, data[k])
    await ctx.store.save_source(src, secret=data.get("secret"))
    await ctx.network.reload_sources()
    ctx.network.refresh_soon()
    return {"source": _public((await ctx.store.get_source(source_id)) or src)}


@router.delete("/sources/{source_id}", tags=["sources"], operation_id="deleteSource", summary="Remove a source (admin)")
async def delete_source(source_id: str, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("admin"))) -> dict[str, bool]:
    if source_id == PUBLIC_SOURCE_ID:
        raise bad_request("The built-in public data source is controlled by Settings > Data sources > 'Use public data'.")
    if not await ctx.store.delete_source(source_id):
        raise not_found("That source")
    await ctx.network.reload_sources()
    return {"ok": True}
