"""The network service: merging node, pool, mempool.space and miner-reported data into one picture,
and recognising a block you found.

Sources are the real implementations talking to the simulators over in-process ASGI: a ``FakeBitcoinCore``
node, and fake Public Pool / mempool.space sites served from the recorded fixtures. The tests call
``NetworkService._poll`` and ``_merge`` directly (never the background loop), so they are deterministic.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

from bsmm.config import RuntimeConfig
from bsmm.context import AppContext
from bsmm.engine.network import (
    PRIORITY,
    PUBLIC_SOURCE_ID,
    SOURCE_CLASSES,
    NetworkService,
    NetworkState,
    SourceHealth,
    _Poller,
)
from bsmm.models import Channel, Severity, Source
from bsmm.notify.channels import CHANNEL_CLASSES, BaseChannel, Notification
from bsmm.sim.axeos import AxeOSSim
from bsmm.sim.bitcoin_core import OTHER_POOL_ADDR, FakeBitcoinCore
from bsmm.sources.base import BlockInfo, NetworkSnapshot, NodeStatus, PoolStatus
from bsmm.sources.bitcoin_core import BitcoinCoreSource
from bsmm.sources.demo import BASE_HEIGHT

FIX = Path(__file__).parent / "fixtures"
ADDR = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"


def fx(path: str) -> Any:
    return json.loads((FIX / path).read_text())


def site(routes: dict[str, Any]) -> Starlette:
    """A fake website: ``{path: json-able | text}``; anything else is a 404."""

    async def handler(request):
        val = routes.get(request.url.path)
        if val is None:
            return PlainTextResponse("nope", status_code=404)
        return PlainTextResponse(val) if isinstance(val, str) else JSONResponse(val)

    return Starlette(routes=[Route("/{p:path}", handler)])


def pool_routes(*, height: int | None = None, difficulty: float | None = None, hashrate: float | None = None) -> dict[str, Any]:
    net = fx("pools/public_pool_network.json")
    net["blocks"] = height if height is not None else net["blocks"]
    net["difficulty"] = difficulty if difficulty is not None else net["difficulty"]
    net["networkhashps"] = hashrate if hashrate is not None else net["networkhashps"]
    return {
        "/api/network": net, "/api/pool": fx("pools/public_pool_pool.json"), "/api/info": fx("pools/public_pool_info.json"),
        f"/api/client/{ADDR}": fx("pools/public_pool_client.json"),
    }


def mempool_routes(*, difficulty: float | None = None, hashrate: float | None = None) -> dict[str, Any]:
    blocks = fx("mempool/blocks.json")
    if difficulty is not None:
        blocks[0]["difficulty"] = difficulty
    hr = fx("mempool/hashrate_3d.json")
    if hashrate is not None:
        hr["currentHashrate"] = hashrate
    return {
        "/api/v1/blocks": blocks, "/api/v1/difficulty-adjustment": fx("mempool/difficulty_adjustment.json"),
        "/api/v1/prices": fx("mempool/prices.json"), "/api/v1/fees/recommended": fx("mempool/fees_recommended.json"),
        "/api/mempool": fx("mempool/mempool.json"), "/api/v1/mining/hashrate/3d": hr, "/api/blocks/tip/height": "972175",
    }


class World:
    """Wires simulated sources into the context's NetworkService, the way the settings page would."""

    def __init__(self, ctx, hosts) -> None:
        self.ctx = ctx
        self.hosts = hosts
        self.net: NetworkService = ctx.network
        self.node: FakeBitcoinCore | None = None
        self.sources: dict[str, Source] = {}

    async def core(self, node: FakeBitcoinCore | None = None, *, password: str = "secret", name: str = "My node") -> FakeBitcoinCore:
        self.node = node or FakeBitcoinCore()
        self.hosts["node.test"] = self.node.app()
        self.sources["core"] = await self.net.add_source(
            "bitcoin_core", name, "http://node.test:8332", {"rpc_user": "umbrel", "rpc_password": password}, None)
        return self.node

    async def pool(self, **overrides: Any) -> Source:
        self.hosts["pool.test"] = site(pool_routes(**overrides))
        self.sources["pool"] = await self.net.add_source("public_pool", "Umbrel pool", "http://pool.test:2019", None, None)
        return self.sources["pool"]

    async def mempool(self, **overrides: Any) -> Source:
        self.hosts["mempool.test"] = site(mempool_routes(**overrides))
        self.sources["mempool"] = await self.net.add_source("mempool_space", "My mempool", "http://mempool.test", None, None)
        return self.sources["mempool"]

    def poller(self, which: str) -> _Poller:
        return self.net._pollers[self.sources[which].id]

    async def cycle(self) -> NetworkState:
        """One pass of the service loop: poll every source, then merge."""
        for p in list(self.net._pollers.values()):
            await self.net._poll(p)
        await self.net._merge()
        return self.net.state

    async def events(self, *types: str) -> list[Any]:
        found = await self.ctx.store.list_events(types=list(types) or None, limit=500)
        return list(reversed(found))  # oldest first


@pytest.fixture
async def world(lan):
    ctx, hosts = lan
    return World(ctx, hosts)


def drain(sub) -> list[Any]:
    out = []
    while not sub.queue.empty():
        msg = sub.queue.get_nowait()
        if msg is not None:
            out.append(msg)
    return out


# --- what each source contributes -----------------------------------------------------------------------------------


async def test_a_node_alone_provides_the_whole_picture(world):
    node = await world.core()
    st = await world.cycle()
    tip = node.blocks[-1]
    assert st.available is True and st.source == "bitcoin_core:My node"
    assert (st.height, st.tip_hash, st.tip_time) == (node.height, tip["hash"], tip["time"])
    assert st.difficulty == pytest.approx(node.difficulty) and st.network_hashrate_hs == 1.0e21
    assert (st.mempool_tx_count, st.mempool_vsize) == (4200, 2_100_000)
    assert st.prices is None and st.btc_price is None and st.fees_sat_vb is None  # a node has no price feed
    assert st.node is not None and st.node.reachable and st.node.synced and st.node.blocks == node.height
    assert [b.height for b in st.recent_blocks] == [node.height - i for i in range(5)]
    assert st.node_behind_by is None and st.stale is False and st.warnings == []
    [h] = st.sources
    assert (h.kind, h.name, h.ok, h.error, h.implicit) == ("bitcoin_core", "My node", True, None, False)
    assert h.last_ok is not None and h.last_poll is not None
    assert st.updated_at == pytest.approx(time.time(), abs=5)


async def test_the_difficulty_epoch_is_worked_out_from_the_nodes_block_times(world):
    node = await world.core()
    st = await world.cycle()
    assert st.epoch is not None
    assert st.epoch["height"] == node.height == 972_174
    assert (st.epoch["epoch_start_height"], st.epoch["next_retarget_height"]) == (971_712, 973_728)
    assert (st.epoch["blocks_into_epoch"], st.epoch["blocks_remaining"]) == (462, 1554)
    assert st.epoch["progress"] == pytest.approx(462 / 2016)
    # the simulated chain has a block exactly every ten minutes, so no change is expected
    assert st.epoch["estimated_change_pct"] == pytest.approx(0.0, abs=1e-9)
    assert st.epoch["seconds_remaining"] == pytest.approx(1554 * 600)
    assert datetime.fromisoformat(st.epoch["estimated_date"]) > datetime.now(UTC)


async def test_halving_figures_follow_the_block_height(world):
    node = await world.core()
    st = await world.cycle()
    h = st.halving
    assert h is not None and h["height"] == node.height
    assert (h["next_halving_height"], h["blocks_remaining"]) == (1_050_000, 1_050_000 - 972_174)
    assert (h["subsidy_now_btc"], h["subsidy_next_btc"]) == (3.125, 1.5625)
    assert h["progress"] == pytest.approx((972_174 % 210_000) / 210_000)
    assert datetime.fromisoformat(h["estimated_date"]) > datetime.now(UTC)
    assert st.subsidy_btc == 3.125


@pytest.mark.parametrize(
    ("height", "subsidy", "next_halving"),
    [(972_174, 3.125, 1_050_000), (1_049_999, 3.125, 1_050_000), (1_050_000, 1.5625, 1_260_000)],
)
async def test_the_subsidy_halves_at_the_halving_height(world, height, subsidy, next_halving):
    await world.ctx.settings.update({"network": {"avg_block_fees_btc": 0.0}})  # the simulated chain always pays 3.125 BTC
    await world.core(FakeBitcoinCore(height=height))
    st = await world.cycle()
    assert st.subsidy_btc == subsidy and st.block_reward_btc == subsidy
    assert st.halving["next_halving_height"] == next_halving


async def test_block_reward_is_the_subsidy_plus_the_average_fees_of_recent_blocks(world):
    node = await world.core()
    st = await world.cycle()
    assert (st.subsidy_btc, st.avg_fees_btc, st.block_reward_btc) == (3.125, 0.0, 3.125)
    node.mine_block(sats=315_000_000)  # pays 0.025 BTC more than the subsidy: that is the block's fees
    st = await world.cycle()
    assert st.avg_fees_btc == pytest.approx(0.025 / 5)  # averaged over the five blocks the node reported
    assert st.block_reward_btc == pytest.approx(3.125 + 0.005)
    await world.ctx.settings.update({"network": {"avg_block_fees_btc": 0.5}})  # a fixed figure from Settings wins
    st = await world.cycle()
    assert st.avg_fees_btc == 0.5 and st.block_reward_btc == pytest.approx(3.625)


async def test_mempool_space_alone_gives_prices_fees_and_the_providers_retarget_estimate(world):
    await world.mempool()
    st = await world.cycle()
    blocks = fx("mempool/blocks.json")
    assert st.available and st.source == "mempool_space:http://mempool.test"
    assert (st.height, st.tip_hash) == (972_175, blocks[0]["id"])
    assert st.difficulty == pytest.approx(140_577_680_051_919.6)
    assert st.network_hashrate_hs == pytest.approx(1.0325e21, rel=1e-3)
    assert (st.mempool_tx_count, st.mempool_vsize) == (50_957, 26_991_314)
    assert st.prices is not None and st.prices["USD"] == 81_788 and st.btc_price == 81_788
    assert st.fees_sat_vb == {"fastest": 5.0, "half_hour": 4.0, "hour": 3.0, "economy": 2.0, "minimum": 1.0}
    assert st.node is None and st.node_behind_by is None
    assert [b.height for b in st.recent_blocks] == [972_175, 972_174, 972_173] and st.recent_blocks[0].pool_name == "AntPool"
    # this source gives no epoch start time, so the epoch leans on mempool.space's own estimate
    ep = st.epoch
    assert ep is not None and ep["blocks_into_epoch"] == 463 and ep["next_retarget_height"] == 973_728
    assert ep["estimated_change_pct"] == pytest.approx(1.369, abs=1e-3)
    assert ep["estimated_date"] == datetime.fromtimestamp(1793347255.369, UTC).isoformat()
    assert ep["seconds_remaining"] == pytest.approx(max(0.0, 1793347255.369 - time.time()), abs=5)
    # fees come straight from the blocks' own totals
    fees = [b["extras"]["totalFees"] for b in blocks]
    assert st.avg_fees_btc == pytest.approx(sum(fees) / len(fees) / 1e8)
    assert st.block_reward_btc == pytest.approx(3.125 + st.avg_fees_btc)


async def test_a_public_pool_provides_network_figures_and_your_workers(world):
    await world.ctx.settings.update({"mining": {"addresses": [ADDR]}})
    await world.pool()
    st = await world.cycle()
    assert st.available and st.source == "public_pool:http://pool.test:2019"
    assert (st.height, st.mempool_tx_count) == (972_175, 4254)
    assert st.difficulty == pytest.approx(140_577_680_051_919.6)
    [pool] = st.pools
    assert pool.kind == "public_pool" and pool.reachable and pool.address == ADDR and pool.pool_miners == 2
    assert sorted(w.name for w in pool.workers) == ["MagicM", "nerdquaxe1"]
    assert pool.hashrate_hs == pytest.approx(7217307095145 + 4845751844569)
    assert st.sources[0].ok is True


async def test_ckpool_adds_pool_statistics_but_no_network_data(world):
    await world.ctx.settings.update({"mining": {"addresses": [ADDR]}})
    world.hosts["ck.test"] = site({"/pool/pool.status": '{"Users":5}\n{"hashrate1m":"1.5P"}\n', f"/users/{ADDR}": fx("pools/ckpool_user.json")})
    world.sources["ck"] = await world.net.add_source("ckpool", "Solo CK", "http://ck.test", None, None)
    st = await world.cycle()
    assert st.available is False and st.source is None and st.height is None  # ckpool does not publish the chain
    [pool] = st.pools
    assert pool.name == "Solo CK" and pool.address == ADDR and pool.pool_miners == 5
    assert pool.best_difficulty_ever == pytest.approx(555308116519205)
    assert st.sources[0].ok is True


async def test_a_ckpool_without_statistics_yet_is_still_reachable(world):
    await world.ctx.settings.update({"mining": {"addresses": [ADDR]}})
    world.hosts["ck.test"] = site({"/pool/pool.status": '{"Users":5}\n'})  # /users/<address> is a 404 until the first share
    world.sources["ck"] = await world.net.add_source("ckpool", "Solo CK", "http://ck.test", None, None)
    st = await world.cycle()
    [pool] = st.pools
    assert pool.reachable and "first share" in (pool.error or "")
    assert st.sources[0].ok is True


# --- merging ---------------------------------------------------------------------------------------------------------


async def test_core_beats_pool_beats_mempool_beats_the_miners_own_figures(world):
    ctx = world.ctx
    await ctx.settings.update({"mining": {"addresses": [ADDR]}})
    node = await world.core(FakeBitcoinCore(difficulty=1.0e14))
    await world.pool(height=972_200, difficulty=2.0e14, hashrate=2.0e21)
    await world.mempool(difficulty=3.0e14, hashrate=3.0e21)
    world.net.set_device_snapshot(972_150, 4.0e14)
    mempool_tip = fx("mempool/blocks.json")[0]["id"]

    st = await world.cycle()  # all four present: the node answers for everything it knows
    assert st.source == "bitcoin_core:My node"
    assert (st.height, st.difficulty, st.network_hashrate_hs) == (node.height, 1.0e14, 1.0e21)
    assert st.mempool_tx_count == 4200  # not the pool's 4254 nor mempool.space's 50957
    # ... and the gaps the node leaves are filled from the next best source
    assert st.prices is not None and st.btc_price == 81_788 and st.fees_sat_vb is not None
    assert st.tip_hash == node.blocks[-1]["hash"] and st.tip_hash != mempool_tip
    assert [h.kind for h in st.sources] == ["bitcoin_core", "public_pool", "mempool_space"] and all(h.ok for h in st.sources)
    heights = [b.height for b in st.recent_blocks]
    assert heights == sorted(heights, reverse=True) and heights[0] == 972_175  # mempool.space has seen one block more
    assert st.node is not None and st.node_behind_by == 1  # the node is one block behind mempool.space

    world.poller("core").snapshot = None  # the node stops contributing (its node status is still reported)
    await world.net._merge()
    st = world.net.state
    assert st.source == "public_pool:http://pool.test:2019"
    assert (st.height, st.difficulty, st.network_hashrate_hs, st.mempool_tx_count) == (972_200, 2.0e14, 2.0e21, 4254)
    assert st.btc_price == 81_788 and st.node is not None

    world.poller("pool").snapshot = None
    await world.net._merge()
    st = world.net.state
    assert st.source == "mempool_space:http://mempool.test"
    assert (st.height, st.difficulty, st.network_hashrate_hs, st.mempool_tx_count) == (972_175, 3.0e14, 3.0e21, 50_957)

    world.poller("mempool").snapshot = None  # only what the miners themselves reported is left
    await world.net._merge()
    st = world.net.state
    assert st.source == "device" and st.available is True
    assert (st.height, st.difficulty) == (972_150, 4.0e14)
    assert st.prices is None and st.btc_price is None and st.recent_blocks == []
    assert st.epoch is not None and st.epoch["height"] == 972_150  # still derived from the height


def test_the_priority_table():
    assert PRIORITY["demo"] < PRIORITY["bitcoin_core"] < PRIORITY["public_pool"] < PRIORITY["mempool_space"] < PRIORITY["device"]
    assert set(SOURCE_CLASSES) == {"bitcoin_core", "public_pool", "ckpool", "mempool_space", "demo"}


def inject(net: NetworkService, kind: str, snap: NetworkSnapshot | None, *, node: NodeStatus | None = None,
           pools: list[PoolStatus] | None = None, ok: bool | None = True) -> _Poller:
    """Put a ready-made snapshot into the service as if ``kind`` had just been polled."""
    src = Source(id=f"src-{kind}", kind=kind, name=f"{kind} source")
    poller = _Poller(src, impl=None, health=SourceHealth(id=src.id, kind=kind, name=src.name, ok=ok),  # type: ignore[arg-type]
                     snapshot=snap, node=node, pools=pools or [])
    net._pollers[src.id] = poller
    return poller


@pytest.mark.parametrize(
    ("present", "winner"),
    [
        ({"bitcoin_core", "public_pool", "mempool_space"}, "bitcoin_core"),
        ({"public_pool", "mempool_space"}, "public_pool"),
        ({"mempool_space"}, "mempool_space"),
        ({"bitcoin_core", "mempool_space"}, "bitcoin_core"),
        ({"bitcoin_core", "public_pool"}, "bitcoin_core"),
    ],
)
async def test_the_best_available_source_headlines_the_state(world, present, winner):
    values = {"bitcoin_core": (100, 1e14), "public_pool": (200, 2e14), "mempool_space": (300, 3e14)}
    for kind in present:
        height, diff = values[kind]
        inject(world.net, kind, NetworkSnapshot(source=kind, height=height, difficulty=diff))
    await world.net._merge()
    st = world.net.state
    assert st.source == winner and (st.height, st.difficulty) == values[winner]


async def test_a_source_without_a_difficulty_does_not_make_the_data_available(world):
    inject(world.net, "mempool_space", NetworkSnapshot(source="mempool_space", height=500, mempool_tx_count=7))
    await world.net._merge()
    st = world.net.state
    assert st.available is False and st.height == 500 and st.mempool_tx_count == 7 and st.difficulty is None


async def test_recent_blocks_are_merged_by_hash_and_the_better_source_wins(world):
    def blk(height: int, h: str, pool: str, **kw: Any) -> BlockInfo:
        return BlockInfo(hash=h, height=height, ts=1e9 + height, pool_name=pool, **kw)

    inject(world.net, "bitcoin_core", NetworkSnapshot(source="core", height=102, difficulty=1e14, recent_blocks=[
        blk(102, "c", "from-node", reward_sats=312_500_000), blk(101, "b", "from-node", reward_sats=312_500_000)]))
    inject(world.net, "mempool_space", NetworkSnapshot(source="mp", height=103, difficulty=1e14, recent_blocks=[
        blk(103, "d", "from-mempool", fees_sats=1), blk(102, "c", "from-mempool", fees_sats=9), blk(101, "b", "from-mempool", fees_sats=9)]))
    await world.net._merge()
    blocks = world.net.state.recent_blocks
    assert [(b.height, b.hash, b.pool_name) for b in blocks] == [(103, "d", "from-mempool"), (102, "c", "from-node"), (101, "b", "from-node")]
    assert blocks[1].fees_sats is None  # the node's copy of the block replaced mempool.space's


async def test_only_the_twelve_newest_blocks_are_kept(world):
    blocks = [BlockInfo(hash=f"h{i}", height=i, ts=1e9 + i) for i in range(1000, 1020)]
    inject(world.net, "mempool_space", NetworkSnapshot(source="mp", height=1019, difficulty=1e14, recent_blocks=blocks))
    await world.net._merge()
    kept = world.net.state.recent_blocks
    assert len(kept) == 12 and kept[0].height == 1019 and kept[-1].height == 1008


async def test_fees_fall_back_from_reported_fees_to_reward_minus_subsidy(world):
    inject(world.net, "mempool_space", NetworkSnapshot(source="mp", height=900_000, difficulty=1e14, recent_blocks=[
        BlockInfo(hash="a", height=900_000, ts=1.0, fees_sats=50_000_000),  # 0.5 BTC reported outright
        BlockInfo(hash="b", height=899_999, ts=1.0, reward_sats=312_500_000 + 150_000_000),  # 1.5 BTC above the subsidy
        BlockInfo(hash="c", height=899_998, ts=1.0, reward_sats=100),  # (reward below the subsidy: ignored)
        BlockInfo(hash="d", height=899_997, ts=1.0),  # (nothing known: ignored)
    ]))
    await world.net._merge()
    assert world.net.state.avg_fees_btc == pytest.approx((0.5 + 1.5) / 2)


async def test_warnings_from_every_source_are_collected(world):
    inject(world.net, "bitcoin_core", NetworkSnapshot(source="core", height=1, difficulty=1.0, warnings=["still syncing"]))
    inject(world.net, "public_pool", NetworkSnapshot(source="pp", height=1, difficulty=1.0, warnings=["pool warning"]))
    await world.net._merge()
    assert sorted(world.net.state.warnings) == ["pool warning", "still syncing"]


async def test_data_older_than_ten_minutes_is_marked_stale(world):
    await world.mempool()
    st = await world.cycle()
    assert st.stale is False
    world.poller("mempool").snapshot.ts -= 601
    await world.net._merge()
    assert world.net.state.stale is True


async def test_the_miners_own_figures_are_a_last_resort_with_nothing_else(world):
    net = world.net
    net.set_device_snapshot(None, None)  # no difficulty: nothing to remember
    await net._merge()
    assert net.state.available is False and net.state.source is None
    net.set_device_snapshot(972_100, 1.4e14)
    await net._merge()
    st = net.state
    assert (st.available, st.source, st.height, st.difficulty) == (True, "device", 972_100, 1.4e14)
    assert st.node is None and st.sources == [] and net.difficulty() == 1.4e14


async def test_without_a_height_there_is_no_epoch_halving_or_reward(world):
    world.net.set_device_snapshot(None, 1.4e14)
    await world.net._merge()
    st = world.net.state
    assert st.available and st.height is None and st.epoch is None and st.halving is None and st.subsidy_btc is None


# --- BTC price -------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("network", "units", "expected"),
    [
        ({}, {}, 81_788),  # default: USD from mempool.space
        ({}, {"currency": "EUR"}, 72_992),
        ({}, {"currency": "eur"}, 72_992),  # case does not matter
        ({}, {"currency": "JPY"}, 12_992_145),
        ({}, {"currency": "XYZ"}, 81_788),  # an unlisted currency falls back to USD
        ({"price_source": "manual", "manual_btc_price": 50_000.0}, {}, 50_000.0),
        ({"price_source": "manual"}, {}, None),  # manual, but no price entered
        ({"price_source": "none"}, {}, None),
    ],
)
async def test_btc_price_follows_the_price_settings(world, network, units, expected):
    await world.ctx.settings.update({"network": network, "units": units})
    await world.mempool()
    st = await world.cycle()
    assert st.btc_price == expected
    assert st.prices is not None and st.prices["USD"] == 81_788  # the raw table is always kept


async def test_a_manual_price_works_without_any_price_feed(world):
    await world.ctx.settings.update({"network": {"price_source": "manual", "manual_btc_price": 42_000.0}})
    await world.core()
    st = await world.cycle()
    assert st.btc_price == 42_000.0 and st.prices is None


# --- node behind the network --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(("node_height", "behind"), [(972_175, 0), (972_174, 1), (972_170, 5), (972_180, 0)])
async def test_node_behind_by_compares_the_node_with_mempool_space(world, node_height, behind):
    await world.core(FakeBitcoinCore(height=node_height))
    await world.mempool()  # its tip is block 972175
    st = await world.cycle()
    assert st.node_behind_by == behind  # ahead of mempool.space counts as zero, not negative


async def test_node_behind_by_is_unknown_when_the_node_is_not_answering(world):
    await world.core(password="wrong")  # the node refuses our login, so we do not know its height
    await world.mempool()  # the reference is there, but there is nothing to compare it with
    st = await world.cycle()
    assert st.node is not None and st.node.reachable is False and st.node_behind_by is None
    assert st.sources[0].ok is False and st.sources[1].ok is True


# --- source health ---------------------------------------------------------------------------------------------------------------


async def test_a_failing_node_raises_source_down_once_and_source_up_on_recovery(world):
    node = await world.core()
    await world.cycle()
    assert await world.events("source_up", "source_down") == []  # a first, successful poll is not news
    core = world.poller("core")

    del world.hosts["node.test"]  # unplugged
    await world.net._poll(core)
    await world.net._poll(core)  # still down: no second event
    await world.net._poll(core)
    [down] = await world.events("source_down")
    assert down.title == "Can't reach My node" and down.severity == Severity.WARNING
    assert down.body and "node.test" in down.body and down.data == {"source_id": world.sources["core"].id}
    assert core.health.ok is False and core.health.error == down.body

    world.hosts["node.test"] = node.app()  # plugged back in
    await world.net._poll(core)
    [up] = await world.events("source_up")
    assert up.title == "My node is reachable again" and up.severity == Severity.SUCCESS
    assert core.health.ok is True and core.health.error is None
    await world.net._poll(core)  # healthy polls stay quiet
    assert len(await world.events("source_up")) == 1


async def test_the_state_fails_over_to_the_next_source_when_the_node_goes_away(world):
    node = await world.core()
    await world.mempool()
    st = await world.cycle()
    assert st.source.startswith("bitcoin_core")
    del world.hosts["node.test"]
    st = await world.cycle()
    assert st.available and st.source.startswith("mempool_space")  # the dashboard does not go blank
    assert st.node is not None and st.node.reachable is False
    assert [h.ok for h in st.sources] == [False, True]
    world.hosts["node.test"] = node.app()
    st = await world.cycle()
    assert st.source.startswith("bitcoin_core") and [h.ok for h in st.sources] == [True, True]


async def test_a_refused_login_is_reported_in_plain_words(world):
    await world.core(password="not-the-password")
    st = await world.cycle()
    assert st.node is not None and st.node.reachable is False
    assert st.sources[0].ok is False and st.sources[0].error == "wrong RPC user name or password"
    [down] = await world.events("source_down")
    assert down.body == "wrong RPC user name or password"
    assert st.available is False  # a node that will not talk provides nothing


async def test_a_node_that_is_still_starting_up_counts_as_down_with_its_own_message(world):
    node = await world.core()
    node.warming_up = True
    st = await world.cycle()
    assert st.node is not None and st.node.reachable is True  # it answers, but says it is not ready
    assert st.sources[0].ok is False and "still starting up" in st.sources[0].error


async def test_a_syncing_node_carries_a_warning_into_the_state(world):
    node = await world.core()
    node.ibd, node.headers_ahead = True, 5000
    st = await world.cycle()
    assert st.node is not None and st.node.synced is False
    assert any("still syncing" in w for w in st.warnings)


async def test_an_unexpected_error_in_a_source_is_contained(world):
    await world.mempool()
    await world.cycle()
    poller = world.poller("mempool")

    async def broken() -> None:
        raise ValueError("boom")

    poller.impl.network = broken  # type: ignore[method-assign]
    await world.net._poll(poller)  # must not raise
    assert poller.health.ok is False and poller.health.error == "ValueError: boom"
    [down] = await world.events("source_down")
    assert down.body == "ValueError: boom"
    await world.net._merge()
    assert world.net.state.available is True  # the last good snapshot is still shown (and will turn 'stale' with time)


async def test_a_public_pool_that_stops_answering_keeps_its_last_snapshot(world):
    await world.pool()
    st = await world.cycle()
    assert st.sources[0].ok is True
    del world.hosts["pool.test"]
    st = await world.cycle()
    assert st.sources[0].ok is False and st.sources[0].error == "no route to host"
    assert st.available is True and st.height == 972_175  # the last reading stays on screen (until it goes stale)


# --- reaction to new blocks: difficulty --------------------------------------------------------------------------------------------


async def test_a_difficulty_change_is_announced_once(world):
    node = await world.core(FakeBitcoinCore(difficulty=1.0e14))
    await world.cycle()
    await world.cycle()
    assert await world.events("difficulty_adjusted") == []  # the first sight of a number is not a change
    node.difficulty = 1.05e14
    await world.cycle()
    await world.cycle()  # unchanged since: nothing more to say
    [up] = await world.events("difficulty_adjusted")
    assert up.title == "Difficulty rose 5.00%" and up.severity == Severity.INFO
    assert up.data["old"] == 1.0e14 and up.data["new"] == 1.05e14 and up.data["pct"] == pytest.approx(5.0)
    assert up.body == "Network difficulty is now 1.05e+14."
    node.difficulty = 1.05e14 / 1.1
    await world.cycle()
    ev = (await world.events("difficulty_adjusted"))[-1]
    assert ev.title == "Difficulty fell 9.09%" and ev.data["pct"] == pytest.approx(-9.0909, abs=1e-3)


async def test_rounding_noise_in_the_difficulty_is_not_a_change(world):
    node = await world.core(FakeBitcoinCore(difficulty=1.0e14))
    await world.cycle()
    node.difficulty = 1.0e14 * (1 + 1e-12)
    await world.cycle()
    assert await world.events("difficulty_adjusted") == []


# --- bus messages ---------------------------------------------------------------------------------------------------------------------


async def test_every_merge_is_published_and_a_new_tip_announces_a_new_block(world):
    node = await world.core()
    sub = world.ctx.bus.subscribe({"network", "new_block"})
    await world.cycle()
    first = drain(sub)
    assert [m.topic for m in first] == ["network"]  # no 'new block' for the very first reading
    assert first[0].data["height"] == node.height and "recent_blocks" not in first[0].data
    assert first[0].data["sources"][0]["ok"] is True
    await world.cycle()
    assert [m.topic for m in drain(sub)] == ["network"]  # same tip: nothing new
    blk = node.mine_block()
    await world.cycle()
    msgs = drain(sub)
    assert [m.topic for m in msgs] == ["new_block", "network"]
    assert msgs[0].data == {"height": node.height, "hash": blk["hash"]}
    sub.close()


# --- block found: end to end ---------------------------------------------------------------------------------------------------------


async def test_a_block_that_pays_your_address_is_recorded_announced_and_published(world):
    ctx = world.ctx
    await ctx.settings.update({"mining": {"addresses": [ADDR]}})
    node = await world.core()
    sub = ctx.bus.subscribe({"block_found"})
    await world.cycle()  # first look: this only sets the 'checked up to here' marker
    assert await ctx.store.kv_get("blocks.last_checked") == node.height
    assert await ctx.store.list_blocks_found() == [] and drain(sub) == []

    block = node.mine_block(address=ADDR, sats=315_000_000, tag="/solo-me/")
    await world.cycle()
    [found] = await ctx.store.list_blocks_found()
    assert found["hash"] == block["hash"] and found["height"] == node.height == block["height"]
    assert found["address"] == ADDR and found["reward_sats"] == 315_000_000 and found["source"] == "chain"
    assert found["device_id"] is None and found["data"] == {"pool": "solo-me", "tx_count": 2000}
    assert await ctx.store.kv_get("blocks.last_checked") == node.height

    [event] = await world.events("block_found")
    assert event.title == "YOU FOUND A BLOCK!" and event.severity == Severity.SUCCESS
    assert event.body == f"Block {node.height:,} matches watched address {ADDR}. This is monitoring evidence, not confirmation of a payout amount."
    assert event.data == {"height": node.height, "hash": block["hash"], "reward_sats": 315_000_000, "address": ADDR, "source": "chain"}
    [msg] = drain(sub)
    assert msg.topic == "block_found"
    assert msg.data == {"height": node.height, "hash": block["hash"], "address": ADDR, "source": "chain"}
    sub.close()


async def test_looking_again_never_records_the_same_block_twice(world):
    ctx = world.ctx
    await ctx.settings.update({"mining": {"addresses": [ADDR]}})
    node = await world.core()
    await world.cycle()
    node.mine_block(address=ADDR)
    await world.cycle()
    await world.cycle()
    await world.cycle()
    assert len(await ctx.store.list_blocks_found()) == 1 and len(await world.events("block_found")) == 1
    # even if the 'checked up to' marker is lost (a restore from backup, say) the database refuses a duplicate
    await ctx.store.kv_set("blocks.last_checked", node.height - 3)
    await world.net._check_blocks(world.net.state, node.height - 1)
    assert len(await ctx.store.list_blocks_found()) == 1 and len(await world.events("block_found")) == 1


async def test_a_block_paid_to_someone_else_is_not_ours(world):
    ctx = world.ctx
    await ctx.settings.update({"mining": {"addresses": [ADDR]}})
    node = await world.core()
    sub = ctx.bus.subscribe({"block_found"})
    await world.cycle()
    for _ in range(3):
        node.mine_block()  # paid to the simulated pool's address
    node.mine_block(address="bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4")  # and one to yet another address
    await world.cycle()
    assert await ctx.store.list_blocks_found() == [] and await world.events("block_found") == [] and drain(sub) == []
    assert await ctx.store.kv_get("blocks.last_checked") == node.height  # but they were looked at
    sub.close()


async def test_without_a_known_payout_address_nothing_can_be_claimed(world):
    node = await world.core()
    assert world.ctx.fleet.all_addresses() == []
    await world.cycle()
    node.mine_block(address=ADDR)
    await world.cycle()
    assert await world.ctx.store.list_blocks_found() == []


async def test_blocks_found_while_the_service_was_busy_are_still_noticed(world):
    ctx = world.ctx
    await ctx.settings.update({"mining": {"addresses": [ADDR]}})
    node = await world.core()
    await world.cycle()
    start = node.height
    for i in range(1, 10):  # nine blocks arrive between two looks; ours is the third
        node.mine_block(address=ADDR if i == 3 else OTHER_POOL_ADDR)
    await world.cycle()  # only the newest five come with the snapshot; the older ones are fetched from the node
    [found] = await ctx.store.list_blocks_found()
    assert found["height"] == start + 3 and found["address"] == ADDR  # (an older block than the snapshot lists, so it was fetched)


async def test_the_catch_up_scan_batches_sixty_blocks_without_skipping(world):
    ctx = world.ctx
    await ctx.settings.update({"mining": {"addresses": [ADDR]}})
    node = await world.core()
    await world.cycle()
    start = node.height
    for i in range(1, 71):
        node.mine_block(address=ADDR if i in (2, 68) else OTHER_POOL_ADDR)
    await world.cycle()
    heights = [b["height"] for b in await ctx.store.list_blocks_found()]
    assert heights == [start + 2]
    assert await ctx.store.kv_get("blocks.last_checked") == start + 60
    await world.cycle()
    assert [b["height"] for b in await ctx.store.list_blocks_found()] == [start + 68, start + 2]


def restarted_service(ctx) -> NetworkService:
    """What the app builds when it starts again: a brand new service over the same database and sources."""
    return NetworkService(ctx.store, ctx.settings, ctx.bus, ctx.events, ctx.http, offline=True, watch_addresses=ctx.fleet.all_addresses)


async def look(net: NetworkService) -> None:
    await net.reload_sources()
    for p in net._pollers.values():
        await net._poll(p)
    await net._merge()


async def test_a_block_found_while_the_app_was_not_running_is_noticed_after_the_restart(world):
    ctx = world.ctx
    await ctx.settings.update({"mining": {"addresses": [ADDR]}})
    node = await world.core()
    await world.cycle()  # the app runs and watches; then it is stopped ...
    start = node.height
    node.mine_block(address=ADDR, sats=315_000_000)  # ... the miners carry on and find a block ...
    node.mine_block()
    node.mine_block()  # ... and the chain moves on
    assert await ctx.store.list_blocks_found() == []

    fresh = restarted_service(ctx)
    await look(fresh)  # the app starts again and takes its first look at the chain
    [found] = await ctx.store.list_blocks_found()
    assert found["height"] == start + 1 and found["address"] == ADDR and found["reward_sats"] == 315_000_000
    assert [e.title for e in await world.events("block_found")] == ["YOU FOUND A BLOCK!"]
    assert await ctx.store.kv_get("blocks.last_checked") == node.height

    await look(restarted_service(ctx))  # restarting again with nothing new changes nothing
    assert len(await ctx.store.list_blocks_found()) == 1 and len(await world.events("block_found")) == 1


async def test_a_fresh_install_starts_from_the_current_tip_and_does_not_claim_old_blocks(world):
    ctx = world.ctx
    await ctx.settings.update({"mining": {"addresses": [ADDR]}})
    node = await world.core()
    node.mine_block(address=ADDR)  # a block that paid this address before the app ever looked
    assert await ctx.store.kv_get("blocks.last_checked") is None
    await world.cycle()
    assert await ctx.store.list_blocks_found() == [] and await ctx.store.kv_get("blocks.last_checked") == node.height
    node.mine_block(address=ADDR)  # from here on, blocks count
    await world.cycle()
    assert [b["height"] for b in await ctx.store.list_blocks_found()] == [node.height]


async def test_a_found_block_reaches_the_users_channels_whatever_their_minimum_severity(world, monkeypatch):
    ctx = world.ctx
    sent: list[Notification] = []

    class Capture(BaseChannel):
        kind = "capture"
        label = "Capture"

        async def send(self, n: Notification) -> None:
            sent.append(n)

    monkeypatch.setitem(CHANNEL_CLASSES, "capture", Capture)
    await ctx.store.save_channel(Channel(id="ch_phone", kind="capture", name="Phone", min_severity=Severity.CRITICAL))
    await ctx.settings.update({"mining": {"addresses": [ADDR]}})
    node = await world.core()
    await world.cycle()
    await ctx.alerts.start()  # the whole chain: chain -> event -> alert rule -> notifier -> channel
    try:
        node.mine_block()  # (an ordinary block is not news)
        node.mine_block(address=ADDR, sats=315_000_000)
        await world.cycle()
        deadline = time.monotonic() + 3
        while not sent and time.monotonic() < deadline:
            await asyncio.sleep(0.01)
    finally:
        await ctx.alerts.stop()
    [n] = sent
    assert n.type == "block_found" and n.title == "YOU FOUND A BLOCK!" and n.severity == Severity.SUCCESS
    assert f"matches watched address {ADDR}" in n.body and n.data["height"] == node.height


async def test_the_payout_address_can_come_from_the_miners_themselves(world):
    ctx = world.ctx
    node = await world.core()
    world.hosts["g.test"] = AxeOSSim("gamma", seed=1, mac="AA:BB:CC:00:00:11").app()  # its stratum user is ADDR.sim1
    res = await ctx.fleet.add_by_host("g.test", drivers=["axeos"])
    await ctx.fleet._poll_once(ctx.fleet.runtimes[res.device.id])
    assert ctx.settings.current.mining.addresses == [] and ctx.fleet.all_addresses() == [ADDR]
    await world.cycle()
    node.mine_block(address=ADDR)
    await world.cycle()
    [found] = await ctx.store.list_blocks_found()
    assert found["address"] == ADDR


async def test_the_context_wires_the_network_service_to_the_fleet(world):
    ctx = world.ctx
    assert ctx.network.watch_addresses == ctx.fleet.all_addresses
    await world.core()
    st = await world.cycle()
    assert ctx.fleet.difficulty_provider() == st.difficulty  # luck accounting uses the merged difficulty


async def test_record_block_found_is_idempotent_across_signals(world):
    ctx = world.ctx
    sub = ctx.bus.subscribe({"block_found"})
    block = BlockInfo(hash="ab" * 32, height=972_176, ts=time.time(), tx_count=1234, pool_name="solo", reward_sats=315_000_000)
    assert await world.net.record_block_found(block, ADDR, source="chain") is True
    assert await world.net.record_block_found(block, ADDR, source="chain") is False
    assert await world.net.record_block_found(block, None, source="device", device_id="dev_1") is False  # a second witness
    [row] = await ctx.store.list_blocks_found()
    assert row["source"] == "chain" and row["device_id"] is None  # the first report stands
    assert len(await world.events("block_found")) == 1 and len(drain(sub)) == 1
    anonymous = BlockInfo(hash="cd" * 32, height=972_177, ts=time.time())
    assert await world.net.record_block_found(anonymous, None, source="device", device_id="dev_1") is True
    ev = (await world.events("block_found"))[-1]
    assert ev.body == "Block 972,177." and ev.data["address"] is None
    sub.close()


async def test_flipping_between_sources_that_disagree_by_a_block_does_not_double_count(lan):
    ctx, _ = lan
    net = NetworkService(ctx.store, ctx.settings, ctx.bus, ctx.events, ctx.http, offline=True, watch_addresses=lambda: [ADDR])
    sub = ctx.bus.subscribe({"new_block"})

    def blk(height: int, address: str) -> BlockInfo:
        return BlockInfo(hash=f"{height:064x}", height=height, ts=1e9 + height, reward_sats=312_500_000, coinbase_addresses=[address])

    def show(height: int, *blocks: BlockInfo) -> None:
        inject(net, "bitcoin_core", NetworkSnapshot(source="core", height=height, difficulty=1e14, recent_blocks=list(blocks)))

    show(100, blk(100, OTHER_POOL_ADDR))
    await net._merge()
    show(101, blk(101, ADDR), blk(100, OTHER_POOL_ADDR))  # we find 101
    await net._merge()
    show(100, blk(100, OTHER_POOL_ADDR))  # the best source briefly shows an older tip ...
    await net._merge()
    show(101, blk(101, ADDR), blk(100, OTHER_POOL_ADDR))  # ... then 101 again
    await net._merge()
    assert [b["height"] for b in await ctx.store.list_blocks_found()] == [101]
    assert len(await ctx.store.list_events(types=["block_found"])) == 1
    assert [m.data["height"] for m in drain(sub)] == [101, 101]  # the tip did move twice; the block was still counted once
    sub.close()


# --- demo mode ----------------------------------------------------------------------------------------------------------------------------


async def test_demo_mode_runs_on_the_built_in_demo_source(tmp_path):
    ctx = await AppContext.create(RuntimeConfig(data_dir=tmp_path, demo=True, offline=True))
    try:
        net = ctx.network
        assert net.demo is True
        await net.reload_sources()
        assert list(net._pollers) == ["demo-data"] and net._pollers["demo-data"].implicit
        await net._poll(net._pollers["demo-data"])
        await net._merge()
        st = net.state
        assert st.available and st.source == "demo" and st.height >= BASE_HEIGHT
        assert st.node is not None and st.node.reachable and st.node.synced
        assert st.btc_price == 82_000.0 and st.fees_sat_vb is not None and len(st.recent_blocks) == 8
        [pool] = st.pools
        assert pool.name == "Demo Public Pool" and pool.workers
        [h] = st.sources
        assert (h.id, h.kind, h.ok, h.implicit) == ("demo-data", "demo", True, True)
        assert st.epoch is not None and st.halving is not None
    finally:
        await ctx.fleet.stop()
        await ctx.http.aclose()
        await ctx.store.close()


async def test_demo_data_outranks_everything_else(lan):
    ctx, _ = lan
    net = NetworkService(ctx.store, ctx.settings, ctx.bus, ctx.events, ctx.http, offline=True, demo=True)
    await net.reload_sources()
    await net._poll(net._pollers["demo-data"])
    inject(net, "bitcoin_core", NetworkSnapshot(source="core", height=1, difficulty=7.0))
    await net._merge()
    assert net.state.source == "demo" and net.state.difficulty != 7.0


# --- which pollers exist ---------------------------------------------------------------------------------------------------------------------


async def test_reload_sources_adds_the_public_source_unless_told_not_to(lan):
    ctx, _ = lan
    net = NetworkService(ctx.store, ctx.settings, ctx.bus, ctx.events, ctx.http, offline=False)
    await net.reload_sources()
    assert list(net._pollers) == [PUBLIC_SOURCE_ID]
    pub = net._pollers[PUBLIC_SOURCE_ID]
    assert pub.implicit and pub.source.kind == "mempool_space" and pub.source.url == "https://mempool.space"
    assert pub.health is not None and pub.health.implicit and pub.health.name == "mempool.space (public)" and pub.health.ok is None
    await net.reload_sources()
    assert net._pollers[PUBLIC_SOURCE_ID] is pub  # unchanged: the same poller (schedule and snapshot) is kept
    await ctx.settings.update({"network": {"mempool_url": "http://mempool.home:3006/"}})
    await net.reload_sources()
    replaced = net._pollers[PUBLIC_SOURCE_ID]
    assert replaced is not pub and replaced.source.url == "http://mempool.home:3006"
    await ctx.settings.update({"network": {"use_public_apis": False}})
    await net.reload_sources()
    assert net._pollers == {}


async def test_offline_mode_never_adds_the_public_source(lan):
    ctx, _ = lan
    assert ctx.network.offline is True
    await ctx.network.reload_sources()
    assert ctx.network._pollers == {}


async def test_an_explicit_mempool_source_replaces_the_public_one(lan):
    ctx, hosts = lan
    hosts["mempool.test"] = site(mempool_routes())
    net = NetworkService(ctx.store, ctx.settings, ctx.bus, ctx.events, ctx.http, offline=False)
    await net.reload_sources()
    assert PUBLIC_SOURCE_ID in net._pollers
    mine = await net.add_source("mempool_space", "Home mempool", "http://mempool.test", None, None)
    assert list(net._pollers) == [mine.id]


async def test_reload_sources_skips_disabled_and_unknown_sources_and_rebuilds_changed_ones(lan):
    ctx, _ = lan
    net = ctx.network
    a = await net.add_source("public_pool", "Pool A", "http://pool.test:2019", None, None)
    b = await net.add_source("mempool_space", "Mempool B", "http://mempool.test", None, None)
    await ctx.store.save_source(Source(id="legacy", kind="mystery", name="From the future"))
    await ctx.store.save_source(Source(id="paused", kind="ckpool", name="Paused", url="http://ck.test", enabled=False))
    await net.reload_sources()
    assert set(net._pollers) == {a.id, b.id}
    before = net._pollers[a.id]
    await net.reload_sources()
    assert net._pollers[a.id] is before
    renamed = a.model_copy(update={"name": "Pool A (renamed)"})
    await ctx.store.save_source(renamed)
    await net.reload_sources()
    assert net._pollers[a.id] is not before and net._pollers[a.id].source.name == "Pool A (renamed)"
    assert all(p.next_due == 0.0 for p in net._pollers.values())  # everything is polled promptly after a change


# --- the wizard's helpers --------------------------------------------------------------------------------------------------------------------------


async def test_test_source_reports_problems_in_plain_words(world):
    world.hosts["node.test"] = FakeBitcoinCore().app()
    good = await world.net.test_source("bitcoin_core", "http://node.test:8332", {"rpc_user": "umbrel", "rpc_password": "secret"})
    assert good.ok and "Connected to /Satoshi:29.0.0/ on main: block 972,174 (fully synced)" in good.message
    bad = await world.net.test_source("bitcoin_core", "http://node.test:8332", {"rpc_user": "umbrel", "rpc_password": "nope"})
    assert not bad.ok and "rejected the login" in bad.message and bad.hints
    unknown = await world.net.test_source("teleporter", None, {})
    assert not unknown.ok and unknown.message == "Unknown source type 'teleporter'."
    blank = await world.net.test_source("bitcoin_core", "", {})
    assert not blank.ok and "enter the node's address" in blank.message
    nowhere = await world.net.test_source("bitcoin_core", "http://nowhere.test:8332", {"rpc_user": "a", "rpc_password": "b"})
    assert not nowhere.ok and "Could not reach the node" in nowhere.message


async def test_add_source_validates_stores_the_secret_encrypted_and_schedules_a_poll(world):
    store = world.ctx.store
    with pytest.raises(ValueError, match="unknown source type 'teleporter'"):
        await world.net.add_source("teleporter", "x", None, None, None)
    src = await world.net.add_source("bitcoin_core", "", "http://node.test:8332", {"rpc_user": "u", "rpc_password": "pw-12345"}, None)
    assert src.name == SOURCE_CLASSES["bitcoin_core"].label and src.has_secret is True  # unnamed sources get their type's label
    assert await store.source_secret(src.id) == {"rpc_user": "u", "rpc_password": "pw-12345"}
    row = await store.db.fetchone("SELECT secret_enc FROM sources WHERE id = ?", (src.id,))
    assert "pw-12345" not in row["secret_enc"]
    poller = world.net._pollers[src.id]
    assert isinstance(poller.impl, BitcoinCoreSource) and poller.next_due == 0.0
    plain = await world.net.add_source("public_pool", "Pool", "http://pool.test:2019", None, None)
    assert plain.has_secret is False and await store.source_secret(plain.id) == {}


async def test_refresh_soon_makes_every_source_due_on_the_next_round(world):
    await world.core()
    await world.pool()
    await world.cycle()
    assert all(p.next_due > time.monotonic() for p in world.net._pollers.values())  # polled just now: each waits its turn
    world.net.refresh_soon()  # the "refresh" button
    assert [p.next_due for p in world.net._pollers.values()] == [0.0, 0.0]


async def test_stop_ends_the_loop_task_and_is_harmless_when_nothing_runs(world):
    net = world.net
    await net.stop()  # never started: nothing to cancel
    assert net._running is False and net._task is None
    for end in (net.stop, net.close_pollers):  # (the shutdown hook just stops the service)
        net._running = True
        net._task = asyncio.create_task(asyncio.sleep(60))  # a stand-in: the real loop is never started in these tests
        await asyncio.wait_for(end(), 5)
        assert net._running is False and net._task.cancelled()
