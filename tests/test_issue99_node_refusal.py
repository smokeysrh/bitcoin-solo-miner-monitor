"""Issue #99: a found node that refuses the app says why and what to change, for people and for agents.

Fake nodes answer like a real Bitcoin Core does: HTTP 403 when ``rpcallowip`` does not cover the caller (before any login is
looked at) and HTTP 401 when the login is missing or wrong. Nothing here touches a real network or node: the TCP sweep is a
table and every HTTP request is routed to an in-process app by host name.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx
import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

import bsmm.engine.discovery as discovery_mod
from bsmm.agent_docs import agent_guide, llms_txt
from bsmm.mcp_server import ApiProblem, _unwrap
from bsmm.models import Source
from bsmm.sim.bitcoin_core import FakeBitcoinCore
from bsmm.sources.bitcoin_core import BitcoinCoreSource

OUR_ADDRESS = "10.7.7.15"
SECRET_PASSWORD = "hunter2-never-shown"
REASONS = {"needs_login", "computer_not_allowed", "unreachable"}


class Refuser:
    """A fake node that answers every request with one status and remembers whether a login was sent."""

    def __init__(self, status: int) -> None:
        self.status = status
        self.authorization_headers: list[str | None] = []

    def app(self) -> Starlette:
        async def handler(request: Request) -> PlainTextResponse:
            self.authorization_headers.append(request.headers.get("authorization"))
            return PlainTextResponse("", status_code=self.status)

        return Starlette(routes=[Route("/", handler, methods=["POST"])])


class FakeTCP:
    def __init__(self) -> None:
        self.open: set[tuple[str, int]] = set()

    async def __call__(self, host: str, port: int, timeout: float = 1.0) -> bool:
        return (host, port) in self.open


@pytest.fixture
def tcp(monkeypatch):
    fake = FakeTCP()
    monkeypatch.setattr(discovery_mod, "tcp_open", fake)
    monkeypatch.setattr(discovery_mod, "own_ipv4_addresses", set)
    monkeypatch.setattr("bsmm.sources.bitcoin_core.local_address_towards", lambda host: OUR_ADDRESS)
    return fake


async def scan(ctx: Any, cidr: str = "10.7.7.0/29") -> Any:
    job = ctx.discovery.start([cidr])
    assert job._task is not None
    _, pending = await asyncio.wait({job._task}, timeout=20)
    assert not pending, f"scan still {job.status}"
    assert job.status == "finished", job.error
    return job


def node_of(job_dict: dict[str, Any], host: str) -> dict[str, Any]:
    return next(s for s in job_dict["sources"] if s["url"] == f"http://{host}:8332")


# --- discovery: the found node says why it refuses --------------------------------------------------------------------------------


async def test_discovery_says_the_node_does_not_allow_this_computer_and_what_to_change(api, tcp):
    c, ctx, hosts = api
    node = Refuser(403)
    hosts["10.7.7.5"] = node.app()
    tcp.open.add(("10.7.7.5", 8332))

    job = await scan(ctx)

    found = node_of((await c.get(f"/api/v1/discovery/{job.id}")).json(), "10.7.7.5")
    refusal = found["refusal"]
    assert refusal["reason"] == "computer_not_allowed"
    assert f"refused this computer ({OUR_ADDRESS})" in refusal["message"]
    assert "rpcallowip=10.7.7.0/24" in refusal["next_step"] and "bitcoin.conf" in refusal["next_step"]
    assert refusal["title"] and refusal["hints"]
    # what the candidate already said is unchanged
    assert (found["kind"], found["needs_credentials"], found["verified"], found["reason"]) == (
        "bitcoin_core", True, False, "Port 8332 (Bitcoin RPC) is open")
    # discovery never sends a login: it asks the node with none
    assert node.authorization_headers == [None]


async def test_discovery_says_the_node_needs_a_login_and_where_to_find_it(api, tcp):
    c, ctx, hosts = api
    node = FakeBitcoinCore()
    hosts["10.7.7.6"] = node.app()
    tcp.open.add(("10.7.7.6", 8332))

    job = await scan(ctx)

    refusal = node_of((await c.get(f"/api/v1/discovery/{job.id}")).json(), "10.7.7.6")["refusal"]
    assert refusal["reason"] == "needs_login"
    assert "Umbrel" in refusal["next_step"] and "Connect" in refusal["next_step"]
    assert "rpcallowip" not in refusal["message"] + refusal["next_step"]
    assert "rejected the login" not in refusal["message"]  # nobody has tried a login yet
    assert node.calls == []  # no RPC method ran


async def test_discovery_gives_an_agent_a_ready_next_step_without_any_secret(api, tcp):
    c, ctx, hosts = api
    hosts["10.7.7.6"] = FakeBitcoinCore().app()
    tcp.open.add(("10.7.7.6", 8332))

    job = await scan(ctx)

    refusal = node_of((await c.get(f"/api/v1/discovery/{job.id}")).json(), "10.7.7.6")["refusal"]
    assert refusal["ask_user_for"] == ["rpc_user", "rpc_password"]
    test_step, add_step = refusal["api_steps"]
    assert (test_step["method"], test_step["path"]) == ("POST", "/api/v1/sources/test")
    assert (add_step["method"], add_step["path"]) == ("POST", "/api/v1/sources")
    for step in (test_step, add_step):
        assert step["body"]["kind"] == "bitcoin_core" and step["body"]["url"] == "http://10.7.7.6:8332"
        assert set(step["body"]["secret"]) == {"rpc_user", "rpc_password"}
        assert all(value.startswith("<") for value in step["body"]["secret"].values())  # placeholders, never a login
    # discovery adds nothing by itself
    assert await ctx.store.list_sources() == []


async def test_discovery_says_a_node_that_does_not_answer_is_unreachable(api, tcp):
    c, ctx, _hosts = api
    tcp.open.add(("10.7.7.5", 8332))  # the port was open a moment ago, but nothing is routed there now

    job = await scan(ctx)

    refusal = node_of((await c.get(f"/api/v1/discovery/{job.id}")).json(), "10.7.7.5")["refusal"]
    assert refusal["reason"] == "unreachable"
    assert "Could not reach the node" in refusal["message"] and refusal["next_step"]
    assert refusal["ask_user_for"] == []


async def test_discovery_does_not_call_something_that_is_not_a_node_a_login_problem(api, tcp):
    _c, ctx, hosts = api
    hosts["10.7.7.5"] = Starlette(routes=[])  # answers every request with 404
    tcp.open.add(("10.7.7.5", 8332))

    job = await scan(ctx)

    refusal = node_of(job.as_dict(), "10.7.7.5")["refusal"]
    assert refusal["reason"] == "unreachable" and "not a Bitcoin Core RPC endpoint" in refusal["message"]


# --- the same facts everywhere ----------------------------------------------------------------------------------------------------


def core_source(client: httpx.AsyncClient, *, url: str, user: str | None = "umbrel", password: str | None = "secret") -> BitcoinCoreSource:
    secret = {k: v for k, v in {"rpc_user": user, "rpc_password": password}.items() if v}
    return BitcoinCoreSource(Source(id="s", kind="bitcoin_core", name="node", url=url), secret, client)


async def test_the_connection_test_and_the_discovery_result_use_the_same_words(api, tcp):
    _c, ctx, hosts = api
    hosts["10.7.7.5"] = Refuser(403).app()
    tcp.open.add(("10.7.7.5", 8332))
    job = await scan(ctx)
    from_discovery = node_of(job.as_dict(), "10.7.7.5")["refusal"]

    result = await core_source(ctx.http, url="http://10.7.7.5:8332").test()

    assert not result.ok and result.refusal is not None
    assert result.refusal.reason == "computer_not_allowed"
    assert (result.message, result.hints) == (from_discovery["message"], from_discovery["hints"])
    assert result.refusal.next_step == from_discovery["next_step"]


@pytest.mark.parametrize(("status", "reason"), [(403, "computer_not_allowed"), (401, "needs_login")])
async def test_a_connection_test_names_the_reason(status, reason):
    transport = httpx.MockTransport(lambda request: httpx.Response(status))
    async with httpx.AsyncClient(transport=transport) as client:
        result = await core_source(client, url="http://192.168.9.79:8332").test()
    assert not result.ok and result.refusal is not None and result.refusal.reason == reason
    assert result.refusal.next_step and result.refusal.hints == result.hints


async def test_a_missing_login_is_reported_as_missing_not_as_rejected():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(401))) as client:
        result = await core_source(client, url="http://192.168.9.79:8332", user=None, password=None).test()
    assert result.refusal is not None and result.refusal.reason == "needs_login"
    assert "rejected the login" not in result.message


async def test_a_connection_that_works_has_no_refusal():
    node = FakeBitcoinCore()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=node.app())) as client:
        source = core_source(client, url="http://node.test:8332")
        result = await source.test()
        status = await source.node()
    assert result.ok and result.refusal is None
    assert status is not None and status.reachable and status.refusal is None


@pytest.mark.parametrize(("status", "reason", "error_word"), [(403, "computer_not_allowed", "rpcallowip"), (401, "needs_login", "password")])
async def test_the_node_status_carries_the_reason_and_keeps_its_error_text(status, reason, error_word):
    transport = httpx.MockTransport(lambda request: httpx.Response(status))
    async with httpx.AsyncClient(transport=transport) as client:
        st = await core_source(client, url="http://192.168.9.79:8332").node()
    assert st is not None and not st.reachable and error_word in (st.error or "")
    assert st.refusal is not None and st.refusal.reason == reason and st.refusal.next_step


async def test_the_node_status_names_an_unreachable_node():
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(refuse)) as client:
        st = await core_source(client, url="http://192.168.9.79:8332").node()
    assert st is not None and st.refusal is not None and st.refusal.reason == "unreachable"


async def test_the_sources_api_and_the_node_endpoint_carry_the_reason(api):
    c, ctx, hosts = api
    hosts["node.test"] = Refuser(403).app()
    src = await ctx.network.add_source("bitcoin_core", "My node", "http://node.test:8332",
                                       {"rpc_user": "umbrel", "rpc_password": SECRET_PASSWORD}, None)
    await ctx.network._poll(ctx.network._pollers[src.id])
    await ctx.network._merge()

    node = (await c.get("/api/v1/node")).json()["node"]
    assert node["refusal"]["reason"] == "computer_not_allowed"
    listed = next(s for s in (await c.get("/api/v1/sources")).json()["sources"] if s["id"] == src.id)
    assert listed["health"]["ok"] is False and listed["health"]["refusal"]["reason"] == "computer_not_allowed"


async def test_a_failed_add_and_test_over_the_api_carry_the_reason_and_never_echo_the_login(api, caplog):
    c, _ctx, hosts = api
    hosts["node.test"] = FakeBitcoinCore().app()
    body = {"kind": "bitcoin_core", "url": "http://node.test:8332", "secret": {"rpc_user": "umbrel", "rpc_password": SECRET_PASSWORD}}
    with caplog.at_level(logging.DEBUG):
        tested = await c.post("/api/v1/sources/test", json=body)
        added = await c.post("/api/v1/sources", json=body)
    assert tested.json()["refusal"]["reason"] == "needs_login"
    assert added.status_code == 422 and added.json()["error"]["details"]["refusal"]["reason"] == "needs_login"
    for text in (tested.text, added.text, caplog.text):
        assert SECRET_PASSWORD not in text


async def test_there_is_one_login_recipe_shared_by_the_form_help_and_the_refusal(api, tcp):
    c, ctx, hosts = api
    hosts["10.7.7.6"] = FakeBitcoinCore().app()
    tcp.open.add(("10.7.7.6", 8332))
    job = await scan(ctx)
    umbrel_line = node_of(job.as_dict(), "10.7.7.6")["refusal"]["hints"][0]
    kinds = (await c.get("/api/v1/sources/kinds")).json()["kinds"]
    help_text = next(k for k in kinds if k["kind"] == "bitcoin_core")["where_to_find_login"]
    assert umbrel_line in help_text


# --- agents -----------------------------------------------------------------------------------------------------------------------


def test_an_mcp_agent_is_told_the_reason_when_adding_a_node_fails():
    error = {"error": {"code": "connection_failed", "message": "The node rejected the login: wrong RPC user name or password",
                       "hint": "Umbrel: open the Bitcoin Node app.", "status": 422,
                       "details": {"ok": False, "refusal": {"reason": "needs_login"}}}}
    with pytest.raises(ApiProblem) as raised:
        _unwrap(httpx.Response(422, json=error))
    assert "needs_login" in str(raised.value)


def test_the_agent_flow_for_a_refusing_node_is_documented_in_the_guide_and_llms_txt():
    guide = agent_guide("http://x:8420")
    flow = guide.get("node_refusal_flow")
    assert flow, "the guide must carry the refusal flow"
    text = llms_txt("http://x:8420")
    for line in flow:
        assert line in text
    joined = " ".join(flow)
    for word in (*REASONS, "refusal", "ask_user_for", "POST /api/v1/sources/test", "POST /api/v1/sources", "GET /api/v1/node"):
        assert word in joined
    assert json.dumps(guide)  # still plain JSON
