"""Issue #45: a Bitcoin Core source is bound to its own cookie file and node address."""

import httpx
import pytest

from bsmm.sim.bitcoin_core import FakeBitcoinCore
from bsmm.sources.base import SourceAuthError
from bsmm.sources.bitcoin_core import BitcoinRPC

COOKIE = "__cookie__:abc123"
OVERSIZED = COOKIE + " " * 65536  # valid login followed by padding: only its size is wrong
NODE_URL = "http://node.test:8332"
OTHER_URL = "http://other.test:8332"


def _nodes(hosts: dict[str, object]) -> tuple[FakeBitcoinCore, FakeBitcoinCore]:
    node = FakeBitcoinCore(user="__cookie__", password="abc123")
    other = FakeBitcoinCore(user="__cookie__", password="abc123")
    hosts["node.test"] = node.app()
    hosts["other.test"] = other.app()
    return node, other


def _body(url: str, cookie_path: object) -> dict[str, object]:
    return {"kind": "bitcoin_core", "name": "My node", "url": url, "options": {"cookie_path": str(cookie_path)}}


async def _saved_sources(c) -> list[object]:
    return (await c.get("/api/v1/sources")).json()["sources"]


async def test_local_node_with_a_normal_cookie_file_keeps_working(api, tmp_path):
    c, _ctx, hosts = api
    _nodes(hosts)
    cookie = tmp_path / ".cookie"
    cookie.write_text(COOKIE)
    tested = await c.post("/api/v1/sources/test", json=_body(NODE_URL, cookie))
    assert tested.status_code == 200 and tested.json()["ok"] is True, tested.text
    added = await c.post("/api/v1/sources", json=_body(NODE_URL, cookie))
    assert added.status_code == 200, added.text
    assert added.json()["source"]["options"] == {"cookie_path": str(cookie)}


async def test_oversized_cookie_file_is_rejected_by_test_and_add(api, tmp_path):
    c, _ctx, hosts = api
    _nodes(hosts)
    cookie = tmp_path / "big.cookie"
    cookie.write_text(OVERSIZED)
    tested = await c.post("/api/v1/sources/test", json=_body(NODE_URL, cookie))
    assert tested.status_code == 200
    assert tested.json()["ok"] is False and "cookie" in tested.json()["message"].lower()
    for query in ("", "?force=true"):
        added = await c.post(f"/api/v1/sources{query}", json=_body(NODE_URL, cookie))
        assert added.status_code in (400, 422), (query, added.text)
        assert "cookie" in added.json()["error"]["message"].lower()
    assert await _saved_sources(c) == []


async def test_cookie_path_that_is_not_a_regular_file_is_rejected(api, tmp_path):
    c, _ctx, hosts = api
    _nodes(hosts)
    folder = tmp_path / "cookie-dir"
    folder.mkdir()
    tested = await c.post("/api/v1/sources/test", json=_body(NODE_URL, folder))
    assert tested.json()["ok"] is False and "cookie" in tested.json()["message"].lower()
    forced = await c.post("/api/v1/sources?force=true", json=_body(NODE_URL, folder))
    assert forced.status_code in (400, 422), forced.text
    assert "cookie" in forced.json()["error"]["message"].lower()
    assert await _saved_sources(c) == []


async def test_rpc_client_refuses_an_oversized_cookie_file(tmp_path):
    node = FakeBitcoinCore(user="__cookie__", password="abc123")
    cookie = tmp_path / "big.cookie"
    cookie.write_text(OVERSIZED)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=node.app()), timeout=5) as client:
        rpc = BitcoinRPC(NODE_URL, client, user=None, password=None, cookie_path=str(cookie))
        with pytest.raises(SourceAuthError):
            await rpc.call("getblockcount")
    assert node.calls == []  # nothing was sent to the node


@pytest.mark.parametrize("resend_saved_path", [False, True])
async def test_cookie_path_does_not_follow_a_changed_host(api, tmp_path, resend_saved_path):
    c, _ctx, hosts = api
    _nodes(hosts)
    cookie = tmp_path / ".cookie"
    cookie.write_text(COOKIE)
    added = await c.post("/api/v1/sources", json=_body(NODE_URL, cookie))
    assert added.status_code == 200, added.text
    patch: dict[str, object] = {"url": OTHER_URL}
    if resend_saved_path:  # the edit form sends the saved options back unchanged
        patch["options"] = {"cookie_path": str(cookie)}
    moved = await c.patch(f"/api/v1/sources/{added.json()['source']['id']}", json=patch)
    assert moved.status_code == 200, moved.text
    assert moved.json()["source"]["url"] == OTHER_URL
    assert "cookie_path" not in moved.json()["source"]["options"]


async def test_cookie_path_survives_same_host_edit_and_can_be_resupplied(api, tmp_path):
    c, _ctx, hosts = api
    _nodes(hosts)
    cookie = tmp_path / ".cookie"
    cookie.write_text(COOKIE)
    fresh = tmp_path / "fresh.cookie"
    fresh.write_text(COOKIE)
    added = await c.post("/api/v1/sources", json=_body(NODE_URL, cookie))
    assert added.status_code == 200, added.text
    source_url = f"/api/v1/sources/{added.json()['source']['id']}"
    same_host = await c.patch(source_url, json={"url": "http://node.test:18332", "name": "Renamed"})
    assert same_host.status_code == 200, same_host.text
    assert same_host.json()["source"]["options"] == {"cookie_path": str(cookie)}
    moved = await c.patch(source_url, json={"url": OTHER_URL, "options": {"cookie_path": str(fresh)}})
    assert moved.status_code == 200, moved.text
    assert moved.json()["source"]["options"] == {"cookie_path": str(fresh)}
