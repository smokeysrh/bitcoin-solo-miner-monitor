"""Issue #98: the Solo blocks list, the latest blocks mempool.space attributes to solo pools.

Nothing here touches the internet: a fake mempool.space answers from tests/fixtures/mempool/solo_pool_blocks.json
and records every request path. Modules of the feature are imported inside the tests so that each test fails
on its own, on the missing behaviour, until the feature exists.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx
import pytest

from bsmm.config import RuntimeConfig
from bsmm.context import AppContext
from bsmm.models import Source
from bsmm.sources.base import BlockInfo
from bsmm.sources.mempool_space import MempoolSpaceSource

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "mempool" / "solo_pool_blocks.json").read_text())
EX_ADDR = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
SOLO_POOLS = [
    ("solock", "Solo CK"),
    ("publicpool", "Public Pool"),
    ("braiinssolo", "Braiins Solo"),
    ("futurebitapollosolo", "FutureBit Apollo Solo"),
    ("solopoolcom", "SoloPool.com"),
]
POOL_PATH = "/api/v1/mining/pool/{slug}/blocks"
#: every fixture block, newest first, with the pool the list must name
EXPECTED = [
    (959001, "Solo CK"),
    (958100, "Braiins Solo"),
    (957382, "Public Pool"),
    (954321, "SoloPool.com"),
    (952000, "FutureBit Apollo Solo"),
    (950210, "Solo CK"),
    (948146, "Public Pool"),
]
PUBLIC_POOL_NEWEST = FIXTURE["publicpool"][0]


class FakeMempool:
    """A fake mempool.space: serves the fixture per pool and records the paths asked for."""

    def __init__(self, *, down: bool = False, failing: frozenset[str] = frozenset()) -> None:
        self.down = down
        self.failing = failing
        self.paths: list[str] = []

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.paths.append(request.url.path)
        if self.down:
            raise httpx.ConnectError("connection refused", request=request)
        slug = request.url.path.removeprefix("/api/v1/mining/pool/").removesuffix("/blocks")
        if slug in self.failing:
            return httpx.Response(500, text="boom")
        if slug not in FIXTURE:
            return httpx.Response(404, text="not found")
        return httpx.Response(200, json=FIXTURE[slug])

    def source(self) -> MempoolSpaceSource:
        client = httpx.AsyncClient(transport=httpx.MockTransport(self._handle), timeout=5)
        return MempoolSpaceSource(Source(id="s", kind="mempool_space", name="m", url="https://mempool.example"), {}, client)


def use_mempool(monkeypatch: pytest.MonkeyPatch, ctx: AppContext, site: FakeMempool) -> None:
    """Make the app's mempool.space source this fake one (the network service is not started in tests)."""
    source = site.source()
    monkeypatch.setattr(ctx.network, "mempool_source", lambda: source, raising=False)


def block(height: int, ts: float, *, hash_: str | None = None) -> BlockInfo:
    return BlockInfo(hash=hash_ or f"{height:064x}", height=height, ts=ts, tx_count=1000)


# ---------------------------------------------------------------------------------------- merge and sort


def test_the_solo_pools_are_the_five_mempool_space_knows_by_slug():
    from bsmm.sources.mempool_space import SOLO_POOLS as pools

    assert [(p.slug, p.name) for p in pools] == SOLO_POOLS


def test_merge_sorts_every_pool_newest_first_and_names_the_pool():
    from bsmm.engine.solo_blocks import merge_solo_blocks
    from bsmm.sources.mempool_space import SOLO_POOLS as pools

    by_pool = {p: [block(h, 1_000 + h) for h in heights] for p, heights in zip(pools, [[100, 90], [95], [105, 80], [], [99]], strict=True)}
    merged = merge_solo_blocks(by_pool)
    assert [b.height for b in merged] == [105, 100, 99, 95, 90, 80]
    assert [b.pool_name for b in merged] == ["Braiins Solo", "Solo CK", "SoloPool.com", "Public Pool", "Solo CK", "Braiins Solo"]
    assert merged[0].pool_slug == "braiinssolo"


def test_merge_keeps_only_the_latest_twenty():
    from bsmm.engine.solo_blocks import SOLO_BLOCKS_LIMIT, merge_solo_blocks
    from bsmm.sources.mempool_space import SOLO_POOLS as pools

    assert SOLO_BLOCKS_LIMIT == 20
    by_pool = {p: [block(1_000 * (i + 1) + n, 5_000 + 10 * n + i) for n in range(10)] for i, p in enumerate(pools)}  # 50 blocks
    merged = merge_solo_blocks(by_pool)
    everything = sorted((b.height for blocks in by_pool.values() for b in blocks), reverse=True)
    assert len(merged) == 20
    assert [b.height for b in merged] == everything[:20]


def test_merge_lists_a_block_once_even_if_two_pool_lists_carry_it():
    from bsmm.engine.solo_blocks import merge_solo_blocks
    from bsmm.sources.mempool_space import SOLO_POOLS as pools

    same = block(500, 9_000, hash_="ab" * 32)
    merged = merge_solo_blocks({pools[0]: [same], pools[1]: [same, block(400, 8_000)]})
    assert [(b.height, b.pool_slug) for b in merged] == [(500, "solock"), (400, "publicpool")]


def test_merge_of_nothing_is_an_empty_list():
    from bsmm.engine.solo_blocks import merge_solo_blocks
    from bsmm.sources.mempool_space import SOLO_POOLS as pools

    assert merge_solo_blocks({p: [] for p in pools}) == []


# ---------------------------------------------------------------------------------------- the REST endpoint


async def test_endpoint_lists_blocks_from_all_pools_newest_first_with_a_mempool_link(api, monkeypatch):
    c, ctx, _ = api
    site = FakeMempool()
    use_mempool(monkeypatch, ctx, site)
    r = await c.get("/api/v1/blocks/solo")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["available"] is True and body["stale"] is False and body["failed_pools"] == []
    assert [(b["height"], b["pool_name"]) for b in body["blocks"]] == EXPECTED
    newest = body["blocks"][0]
    assert newest["hash"] == FIXTURE["solock"][0]["id"]
    assert newest["ts"] == FIXTURE["solock"][0]["timestamp"]
    assert newest["url"] == f"https://mempool.space/block/{newest['hash']}"
    assert [p["slug"] for p in body["pools"]] == [slug for slug, _ in SOLO_POOLS]
    assert body["limit"] == 20
    assert sorted(site.paths) == sorted(POOL_PATH.format(slug=slug) for slug, _ in SOLO_POOLS)


async def test_a_found_block_of_the_user_is_marked_yours(api, monkeypatch):
    c, ctx, _ = api
    use_mempool(monkeypatch, ctx, FakeMempool())
    before = (await c.get("/api/v1/blocks/solo")).json()
    assert before["blocks"] and not any(b["yours"] for b in before["blocks"])
    await ctx.store.add_block_found(
        hash_=PUBLIC_POOL_NEWEST["id"], height=PUBLIC_POOL_NEWEST["height"], ts=PUBLIC_POOL_NEWEST["timestamp"],
        device_id=None, address=EX_ADDR, reward_sats=None, source="chain", data={"pool": "Public Pool"},
    )
    after = (await c.get("/api/v1/blocks/solo")).json()
    assert [b["height"] for b in after["blocks"] if b["yours"]] == [957382]
    assert all(isinstance(b["yours"], bool) for b in after["blocks"])


async def test_a_found_block_that_was_replaced_is_not_marked_yours(api, monkeypatch):
    c, ctx, _ = api
    use_mempool(monkeypatch, ctx, FakeMempool())
    await ctx.store.add_block_found(
        hash_=PUBLIC_POOL_NEWEST["id"], height=PUBLIC_POOL_NEWEST["height"], ts=PUBLIC_POOL_NEWEST["timestamp"],
        device_id=None, address=EX_ADDR, reward_sats=None, source="chain", data={},
    )
    assert await ctx.store.set_block_orphaned(PUBLIC_POOL_NEWEST["id"], time.time())
    body = (await c.get("/api/v1/blocks/solo")).json()
    assert body["blocks"] and not any(b["yours"] for b in body["blocks"])


async def test_a_second_look_is_answered_from_the_cache_until_it_expires(api, monkeypatch):
    c, ctx, _ = api
    site = FakeMempool()
    use_mempool(monkeypatch, ctx, site)
    assert (await c.get("/api/v1/blocks/solo")).status_code == 200
    assert (await c.get("/api/v1/blocks/solo")).status_code == 200
    assert len(site.paths) == len(SOLO_POOLS), "one request per pool, however often the page is opened"

    from bsmm.engine.solo_blocks import SOLO_BLOCKS_CACHE_S

    start = time.monotonic()
    ctx.solo_blocks.clock = lambda: start + SOLO_BLOCKS_CACHE_S + 1
    assert (await c.get("/api/v1/blocks/solo")).status_code == 200
    assert len(site.paths) == 2 * len(SOLO_POOLS)


async def test_outside_lookups_off_is_a_plain_message_not_an_error_or_an_empty_list(api):
    c, ctx, _ = api
    r = await c.get("/api/v1/blocks/solo")  # the test app runs offline and has no mempool source
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["available"] is False and body["blocks"] == [] and body["error"] is None
    assert "offline" in body["message"].lower()

    ctx.network.offline = False
    await ctx.settings.update({"network": {"use_public_apis": False}})
    body = (await c.get("/api/v1/blocks/solo")).json()
    assert body["available"] is False and body["blocks"] == []
    assert "Use mempool.space" in body["message"]


async def test_an_unreachable_mempool_is_an_error_never_an_empty_list(api, monkeypatch):
    c, ctx, _ = api
    use_mempool(monkeypatch, ctx, FakeMempool(down=True))
    r = await c.get("/api/v1/blocks/solo")
    assert r.status_code == 502
    err = r.json()["error"]
    assert err["code"] == "solo_blocks_unavailable"
    assert "connection refused" in err["message"]
    assert "blocks" not in r.json()


async def test_one_pool_failing_returns_the_rest_and_names_the_missing_pool(api, monkeypatch):
    c, ctx, _ = api
    use_mempool(monkeypatch, ctx, FakeMempool(failing=frozenset({"publicpool"})))
    r = await c.get("/api/v1/blocks/solo")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["available"] is True and body["failed_pools"] == ["Public Pool"]
    assert [b["height"] for b in body["blocks"]] == [959001, 958100, 954321, 952000, 950210]


async def test_a_failed_refresh_keeps_the_last_list_marked_stale(api, monkeypatch):
    c, ctx, _ = api
    site = FakeMempool()
    use_mempool(monkeypatch, ctx, site)
    first = (await c.get("/api/v1/blocks/solo")).json()
    assert [b["height"] for b in first["blocks"]] == [h for h, _ in EXPECTED]

    from bsmm.engine.solo_blocks import SOLO_BLOCKS_CACHE_S

    start = time.monotonic()
    ctx.solo_blocks.clock = lambda: start + SOLO_BLOCKS_CACHE_S + 1
    site.down = True
    r = await c.get("/api/v1/blocks/solo")
    assert r.status_code == 200, r.text
    stale = r.json()
    assert stale["stale"] is True and "connection refused" in stale["error"]
    assert [b["height"] for b in stale["blocks"]] == [h for h, _ in EXPECTED]

    site.down = False
    recovered = (await c.get("/api/v1/blocks/solo")).json()
    assert recovered["stale"] is False and recovered["error"] is None


async def test_the_endpoint_is_in_the_openapi_schema_and_the_agent_docs(api):
    from bsmm.agent_docs import llms_txt

    c, _, _ = api
    schema = (await c.get("/openapi.json")).json()
    assert schema["paths"]["/api/v1/blocks/solo"]["get"]["operationId"] == "getSoloBlocks"
    assert "/api/v1/blocks/solo" in llms_txt("http://x:8420")


# ---------------------------------------------------------------------------------------- demo mode


@pytest.fixture
async def demo_ctx(tmp_path):
    def forbidden(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"demo mode made an outside request: {request.url}")

    http = httpx.AsyncClient(transport=httpx.MockTransport(forbidden))
    ctx = await AppContext.create(RuntimeConfig(data_dir=tmp_path, demo=True, offline=True), http=http)
    yield ctx
    await ctx.fleet.stop()
    await ctx.http.aclose()
    await ctx.store.close()


async def test_demo_mode_serves_the_same_synthetic_blocks_without_any_outside_call(demo_ctx):
    from bsmm.api.app import create_app

    app = create_app(ctx=demo_ctx)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as c:
        first = await c.get("/api/v1/blocks/solo")
        second = await c.get("/api/v1/blocks/solo")
    assert first.status_code == 200, first.text
    a, b = first.json(), second.json()
    assert a["available"] is True and a["source"] == "demo"
    assert len(a["blocks"]) == 20
    heights = [x["height"] for x in a["blocks"]]
    assert heights == sorted(heights, reverse=True) and len(set(heights)) == 20
    assert {x["pool_name"] for x in a["blocks"]} <= {name for _, name in SOLO_POOLS}
    assert all(x["url"] == f"https://mempool.space/block/{x['hash']}" for x in a["blocks"])
    assert all(x["ts"] <= time.time() for x in a["blocks"])
    key = [(x["height"], x["hash"], x["pool_name"]) for x in a["blocks"]]
    assert key == [(x["height"], x["hash"], x["pool_name"]) for x in b["blocks"]], "the demo list is the same every time"
