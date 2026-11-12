"""Issue #2386: a login typed into a source's address is refused, and one already saved is hidden in source output.

The user name and password for a Bitcoin node belong in the RPC login fields (``secret``), never in the address.
Everything here runs the real API app over the in-process test network from ``conftest``.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from bsmm.api.app import create_app
from bsmm.models import Source
from bsmm.sources.bitcoin_core import normalise_url

PASSWORD = "hunter2secret"
LOGIN_URLS = [
    f"http://rpcuser:{PASSWORD}@node.test:8332",
    "http://rpcuser:123456@node.test:8332",
    f"rpcuser:{PASSWORD}@node.test",
    f"https://rpcuser@node.test/{PASSWORD}",
]
SAVED_URL = f"http://rpcuser:{PASSWORD}@node.test:8332"


def assert_refused_without_echo(r: httpx.Response) -> None:
    assert r.status_code == 400, r.text
    error = r.json()["error"]
    assert error["code"] == "bad_request"
    text = f"{error['message']} {error.get('hint') or ''}"
    assert "RPC user" in text and "RPC password" in text  # says where the login goes
    assert PASSWORD not in r.text and "123456" not in r.text  # never repeats the login back


@pytest.mark.parametrize("url", LOGIN_URLS)
@pytest.mark.parametrize("query", ["", "?force=true"])
async def test_adding_a_source_with_a_login_in_its_address_is_refused(api, url: str, query: str):
    c, ctx, _ = api

    r = await c.post(f"/api/v1/sources{query}", json={"kind": "bitcoin_core", "url": url})

    assert_refused_without_echo(r)
    assert await ctx.store.list_sources() == []


async def test_adding_a_switched_off_source_with_a_login_in_its_address_is_refused(api):
    c, ctx, _ = api

    r = await c.post("/api/v1/sources", json={"kind": "public_pool", "url": SAVED_URL, "enabled": False})

    assert_refused_without_echo(r)
    assert await ctx.store.list_sources() == []


async def test_editing_a_source_to_have_a_login_in_its_address_is_refused(api):
    c, ctx, _ = api
    added = await c.post("/api/v1/sources", json={"kind": "public_pool", "url": "http://pool.test:2019", "enabled": False})
    assert added.status_code == 200, added.text
    source_id = added.json()["source"]["id"]

    r = await c.patch(f"/api/v1/sources/{source_id}", json={"url": SAVED_URL})

    assert_refused_without_echo(r)
    stored = await ctx.store.get_source(source_id)
    assert stored is not None and stored.url == "http://pool.test:2019"


async def test_a_source_address_without_a_login_is_still_saved_and_edited(api):
    c, ctx, _ = api
    added = await c.post("/api/v1/sources", json={"kind": "bitcoin_core", "url": "http://node.test:8332/wallet/x@y", "enabled": False,
                                                     "secret": {"rpc_user": "rpcuser", "rpc_password": PASSWORD}})
    assert added.status_code == 200, added.text
    source = added.json()["source"]
    assert source["url"] == "http://node.test:8332/wallet/x@y" and source["has_secret"] is True

    edited = await c.patch(f"/api/v1/sources/{source['id']}", json={"url": "http://other.test:8332"})

    assert edited.status_code == 200, edited.text
    assert edited.json()["source"]["url"] == "http://other.test:8332"
    assert (await ctx.store.source_secret(source["id"])) == {"rpc_user": "rpcuser", "rpc_password": PASSWORD}


async def test_a_saved_source_address_with_a_login_is_hidden_in_source_output(api):
    c, ctx, _ = api
    await ctx.store.save_source(Source(id="src_old", kind="public_pool", name="Old pool", url=SAVED_URL, enabled=False))
    assert (await c.post("/api/v1/auth/password", json={"new_password": "correct horse battery"})).status_code == 200
    token = (await c.post("/api/v1/auth/tokens", json={"name": "agent", "scope": "read"})).json()["token"]
    reader = httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(ctx=ctx)), base_url="http://bsmm.test",
                               headers={"Authorization": f"Bearer {token}"})
    try:
        r = await reader.get("/api/v1/sources")
    finally:
        await reader.aclose()

    assert r.status_code == 200, r.text
    assert PASSWORD not in r.text and "rpcuser" not in r.text
    [item] = [s for s in r.json()["sources"] if s["id"] == "src_old"]
    assert item["url"] == "http://***@node.test:8332"
    stored = await ctx.store.get_source("src_old")  # nothing is rewritten in storage
    assert stored is not None and stored.url == SAVED_URL


async def test_editing_other_fields_of_a_saved_source_with_a_login_hides_it_in_the_answer(api):
    c, ctx, _ = api
    await ctx.store.save_source(Source(id="src_old", kind="public_pool", name="Old pool", url=SAVED_URL, enabled=False))

    r = await c.patch("/api/v1/sources/src_old", json={"name": "Renamed"})

    assert r.status_code == 200, r.text
    body: dict[str, Any] = r.json()["source"]
    assert body["name"] == "Renamed" and body["url"] == "http://***@node.test:8332"
    assert PASSWORD not in r.text


def test_normalise_url_does_not_read_a_port_out_of_a_login():
    for url in ("http://rpcuser:8332@node.test", "rpcuser:8332@node.test", "http://rpcuser:8332@node.test:18332"):
        with pytest.raises(ValueError, match="RPC user"):
            normalise_url(url)


def test_normalise_url_leaves_ordinary_addresses_unchanged():
    assert normalise_url("192.168.1.5") == "http://192.168.1.5:8332"
    assert normalise_url("https://node:18443") == "https://node:18443"
    assert normalise_url("http://[::1]:8332/") == "http://[::1]:8332"
    assert normalise_url("http://umbrel.local:8332/wallet/x@y") == "http://umbrel.local:8332"
