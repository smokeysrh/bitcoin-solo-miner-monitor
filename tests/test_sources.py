import json
from pathlib import Path

import httpx
import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

from bsmm.models import Source
from bsmm.sim.bitcoin_core import FakeBitcoinCore
from bsmm.sources.base import SourceAuthError, SourceUnreachable
from bsmm.sources.bitcoin_core import (
    ALLOWED_METHODS,
    BitcoinCoreSource,
    BitcoinRPC,
    RpcError,
    coinbase_tag,
    normalise_url,
)
from bsmm.sources.ckpool import CkpoolSource, parse_pool_status, parse_user_document
from bsmm.sources.mempool_space import MempoolSpaceSource
from bsmm.sources.public_pool import PublicPoolSource

FIX = Path(__file__).parent / "fixtures"
EX_ADDR = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"


def j(path: str):
    return json.loads((FIX / path).read_text())


def fake_site(routes: dict[str, object]) -> httpx.AsyncClient:
    """An httpx client whose every request is answered from a dict {path: json-able}."""

    async def handler(request):
        path = request.url.path
        if path in routes:
            val = routes[path]
            if isinstance(val, str):
                return PlainTextResponse(val)
            if isinstance(val, int):
                return PlainTextResponse(str(val), status_code=val) if val >= 400 else JSONResponse(val)
            return JSONResponse(val)
        return PlainTextResponse("nope", status_code=404)

    app = Starlette(routes=[Route("/{p:path}", handler)])
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), timeout=5)


# --- Public Pool ---------------------------------------------------------------------------------------


async def test_public_pool_network_and_pool_stats():
    routes = {
        "/api/network": j("pools/public_pool_network.json"),
        "/api/pool": j("pools/public_pool_pool.json"),
        "/api/info": j("pools/public_pool_info.json"),
        f"/api/client/{EX_ADDR}": j("pools/public_pool_client.json"),
    }
    async with fake_site(routes) as c:
        src = PublicPoolSource(Source(id="s", kind="public_pool", name="Umbrel pool", url="http://umbrel.local:2019"), {}, c)
        net = await src.network()
        assert net and net.height == 972175 and net.difficulty == pytest.approx(140577680051919.6)
        assert net.network_hashrate_hs == pytest.approx(1.062722434937897e21)
        [st] = await src.pool([EX_ADDR])
    assert st.reachable and st.pool_miners == 2
    assert st.blocks_found == 0
    assert len(st.workers) == 2
    assert st.best_difficulty == pytest.approx(122008164580.62956)
    names = {w.name for w in st.workers}
    assert names == {"MagicM", "nerdquaxe1"}
    nq = next(w for w in st.workers if w.name == "nerdquaxe1")
    assert nq.best_difficulty == pytest.approx(50999706655.81)  # string in the API, parsed to float
    assert nq.hashrate_hs == pytest.approx(4845751844569)
    assert nq.started and nq.last_seen and nq.last_seen > nq.started
    assert st.hashrate_hs == pytest.approx(sum(w.hashrate_hs or 0 for w in st.workers))


async def test_public_pool_test_button_messages():
    good = {"/api/network": j("pools/public_pool_network.json"), "/api/pool": j("pools/public_pool_pool.json")}
    async with fake_site(good) as c:
        r = await PublicPoolSource(Source(id="s", kind="public_pool", name="p", url="http://x:2019/api"), {}, c).test()
    assert r.ok and "block 972,175" in r.message
    async with fake_site({}) as c:
        r = await PublicPoolSource(Source(id="s", kind="public_pool", name="p", url="http://x:2018"), {}, c).test()
    assert not r.ok and any("2019" in h for h in r.hints)


async def test_public_pool_chart():
    routes = {f"/api/client/{EX_ADDR}/chart": j("pools/public_pool_client_chart.json")}
    async with fake_site(routes) as c:
        pts = await PublicPoolSource(Source(id="s", kind="public_pool", name="p", url="http://x"), {}, c).hashrate_chart(EX_ADDR)
    assert len(pts) == 36 and pts[0][0] < pts[-1][0] and pts[0][1] > 1e12


# --- ckpool ----------------------------------------------------------------------------------------------


def test_ckpool_user_document():
    st = parse_user_document(j("pools/ckpool_user.json"), EX_ADDR, "solo.ckpool.org")
    assert st.best_difficulty_ever == pytest.approx(555308116519205)
    assert st.extra["hashrate_1d_hs"] == pytest.approx(312e12)
    assert st.extra["hashrate_1h_hs"] == pytest.approx(221e6)
    assert [w.name for w in st.workers] == ["rig1", "rig2"]
    assert st.workers[0].hashrate_hs == 0 and st.last_share and st.shares


def test_ckpool_pool_status_lines():
    text = (
        '{"runtime":1092810,"lastupdate":1792424652,"Users":23259,"Workers":37724}\n'
        '{"hashrate1m":"93.2P","hashrate5m":"93.7P"}\n'
        '{"diff":162.7,"accepted":1,"SPS1m":5502.5}\n'
    )
    info = parse_pool_status(text)
    assert info["Users"] == 23259 and info["hashrate1m"] == "93.2P" and info["SPS1m"] == 5502.5


async def test_ckpool_source_flow_and_missing_address():
    routes = {
        "/pool/pool.status": '{"Users":5}\n{"hashrate1m":"1.5P"}\n',
        f"/users/{EX_ADDR}": j("pools/ckpool_user.json"),
    }
    async with fake_site(routes) as c:
        src = CkpoolSource(Source(id="s", kind="ckpool", name="solo", url="https://solo.example"), {}, c)
        [st] = await src.pool([EX_ADDR])
        [missing] = await src.pool(["bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"])
        res = await src.test()
    assert st.pool_miners == 5 and st.pool_hashrate_hs == pytest.approx(1.5e15)
    assert missing.reachable and missing.error and "first share" in missing.error
    assert res.ok


# --- mempool.space ----------------------------------------------------------------------------------------


async def test_mempool_space_snapshot():
    routes = {
        "/api/v1/blocks": j("mempool/blocks.json"),
        "/api/v1/difficulty-adjustment": j("mempool/difficulty_adjustment.json"),
        "/api/v1/prices": j("mempool/prices.json"),
        "/api/v1/fees/recommended": j("mempool/fees_recommended.json"),
        "/api/mempool": j("mempool/mempool.json"),
        "/api/v1/mining/hashrate/3d": j("mempool/hashrate_3d.json"),
        "/api/blocks/tip/height": "972175",
    }
    async with fake_site(routes) as c:
        src = MempoolSpaceSource(Source(id="s", kind="mempool_space", name="m", url="https://mempool.example"), {}, c)
        snap = await src.network()
        test = await src.test()
    assert snap and snap.height == 972175
    assert snap.difficulty == pytest.approx(140577680051919.6)
    assert snap.network_hashrate_hs == pytest.approx(1.0325e21, rel=1e-3)
    assert snap.est_difficulty_change_pct == pytest.approx(1.369, abs=1e-3)
    assert snap.prices and snap.prices["USD"] > 1000
    assert snap.fees_sat_vb and snap.fees_sat_vb["fastest"] >= 1
    assert snap.mempool_tx_count == 50957
    assert len(snap.recent_blocks) == 3 and snap.recent_blocks[0].pool_name == "AntPool"
    assert snap.recent_blocks[0].coinbase_addresses
    assert test.ok and "972,175" in test.message


async def test_mempool_space_survives_partial_failure():
    routes = {"/api/v1/blocks": j("mempool/blocks.json")}  # everything else 404s
    async with fake_site(routes) as c:
        snap = await MempoolSpaceSource(Source(id="s", kind="mempool_space", name="m"), {}, c).network()
    assert snap and snap.height == 972175 and snap.prices is None and snap.fees_sat_vb is None


# --- Bitcoin Core ------------------------------------------------------------------------------------------


def core_client(node: FakeBitcoinCore) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=node.app()), timeout=5)


def core_source(c, password="secret", url="http://node.test:8332"):
    return BitcoinCoreSource(Source(id="n", kind="bitcoin_core", name="My node", url=url), {"rpc_user": "umbrel", "rpc_password": password}, c)


async def test_core_node_status():
    node = FakeBitcoinCore()
    async with core_client(node) as c:
        st = await core_source(c).node()
    assert st and st.reachable and st.synced
    assert st.version == "29.0.0" and st.subversion == "/Satoshi:29.0.0/" and st.chain == "main"
    assert st.blocks == node.height and st.headers == node.height
    assert st.connections == 18 and st.connections_in == 6 and st.connections_out == 12
    assert st.mempool_tx_count == 4200
    assert st.min_relay_fee_sat_vb == pytest.approx(1.0)
    assert st.network_hashrate_hs == pytest.approx(1e21)


async def test_core_syncing_node_is_not_reported_synced():
    node = FakeBitcoinCore()
    node.ibd = True
    node.headers_ahead = 5000
    async with core_client(node) as c:
        st = await core_source(c).node()
    assert st and st.reachable and not st.synced


async def test_core_wrong_password_gives_actionable_test_result():
    node = FakeBitcoinCore()
    async with core_client(node) as c:
        res = await core_source(c, password="wrong").test()
        st = await core_source(c, password="wrong").node()
    assert not res.ok and "rejected the login" in res.message
    assert any("Umbrel" in h for h in res.hints)
    assert st and not st.reachable and "password" in (st.error or "")


async def test_core_warming_up_is_reported_not_crashed():
    node = FakeBitcoinCore()
    node.warming_up = True
    async with core_client(node) as c:
        st = await core_source(c).node()
        res = await core_source(c).test()
    assert st and st.reachable and "starting up" in (st.error or "")
    assert not res.ok


async def test_core_unreachable():
    async with httpx.AsyncClient(timeout=1) as c:
        res = await core_source(c, url="http://127.0.0.1:9").test()
    assert not res.ok and "Could not reach" in res.message


async def test_core_network_snapshot_with_blocks_and_epoch():
    node = FakeBitcoinCore()
    async with core_client(node) as c:
        snap = await core_source(c).network()
    assert snap and snap.height == node.height
    assert snap.difficulty == pytest.approx(node.difficulty)
    assert snap.epoch_start_time is not None and snap.epoch_start_time < snap.tip_time  # type: ignore[operator]
    assert len(snap.recent_blocks) == 5
    top = snap.recent_blocks[0]
    assert top.height == node.height and top.coinbase_addresses and top.pool_name == "FakePool"
    assert top.reward_sats == 312_500_000


async def test_core_block_info_sees_a_block_we_mined():
    node = FakeBitcoinCore()
    node.mine_block(address=EX_ADDR, sats=315_000_000, tag="/solo-me/")
    async with core_client(node) as c:
        b = await core_source(c).block_info(node.height)
    assert b and b.coinbase_addresses == [EX_ADDR] and b.reward_sats == 315_000_000 and b.pool_name == "solo-me"


async def test_rpc_client_refuses_wallet_and_write_methods():
    node = FakeBitcoinCore()
    async with core_client(node) as c:
        rpc = BitcoinRPC("node.test", c, user="umbrel", password="secret")
        for bad in ("sendtoaddress", "getwalletinfo", "dumpprivkey", "stop", "submitblock", "sendrawtransaction"):
            with pytest.raises(RpcError):
                await rpc.call(bad)
        with pytest.raises(RpcError):
            await rpc.batch([("getblockcount", []), ("walletpassphrase", ["x", 1])])
    assert node.calls == []  # nothing reached the node
    assert not {"sendtoaddress", "getwalletinfo", "stop"} & ALLOWED_METHODS


async def test_rpc_cookie_file_auth(tmp_path):
    node = FakeBitcoinCore(user="__cookie__", password="abc123")
    cookie = tmp_path / ".cookie"
    cookie.write_text("__cookie__:abc123")
    async with core_client(node) as c:
        rpc = BitcoinRPC("http://node.test", c, user=None, password=None, cookie_path=str(cookie))
        assert await rpc.call("getblockcount") == node.height
        missing = BitcoinRPC("http://node.test", c, user=None, password=None, cookie_path=str(tmp_path / "nope"))
        with pytest.raises(SourceAuthError):
            await missing.call("getblockcount")


def test_normalise_url():
    assert normalise_url("192.168.1.5") == "http://192.168.1.5:8332"
    assert normalise_url("http://umbrel.local:8332/wallet/x") == "http://umbrel.local:8332"
    assert normalise_url("https://node:18443") == "https://node:18443"
    with pytest.raises(ValueError):
        normalise_url("")


def test_coinbase_tag():
    assert coinbase_tag((b"\x03\x01\x02\x03/AntPool/\x00").hex()) == "AntPool"
    assert coinbase_tag("zz") is None
    assert coinbase_tag(None) is None
    assert coinbase_tag("0102") is None


async def test_unreachable_error_type():
    async with httpx.AsyncClient(timeout=1) as c:
        rpc = BitcoinRPC("127.0.0.1:9", c, user="a", password="b", timeout=1)
        with pytest.raises(SourceUnreachable):
            await rpc.call("getblockcount")
async def test_core_forbidden_is_not_reported_as_a_wrong_password(monkeypatch):
    # Bitcoin Core answers 403 (rpcallowip) before it looks at any login. Telling the user their
    # password is wrong sent them hunting for the wrong problem.
    monkeypatch.setattr("bsmm.sources.bitcoin_core.local_address_towards", lambda host: "192.168.9.15")
    transport = httpx.MockTransport(lambda request: httpx.Response(403))
    async with httpx.AsyncClient(transport=transport) as c:
        res = await core_source(c, url="http://192.168.9.79:8332").test()
        st = await core_source(c, url="http://192.168.9.79:8332").node()
    assert not res.ok
    assert "refused this computer (192.168.9.15)" in res.message and "rejected the login" not in res.message
    assert any("rpcallowip=192.168.9.0/24" in h for h in res.hints)
    assert st and not st.reachable and "rpcallowip" in (st.error or "")
async def test_core_wrong_password_still_says_wrong_password():
    node = FakeBitcoinCore()
    async with core_client(node) as c:
        res = await core_source(c, password="wrong").test()
    assert "rejected the login" in res.message and "rpcallowip" not in res.message
def test_local_address_towards_loopback_and_garbage():
    from bsmm.net import local_address_towards
    assert local_address_towards("127.0.0.1") == "127.0.0.1"
    assert local_address_towards("no-such-host.invalid") is None
