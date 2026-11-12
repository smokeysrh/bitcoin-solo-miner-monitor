"""Issue #2376: a Bitcoin node saved by host name is recognised when a scan finds it by its IP address.

A scan reports the node it finds as ``http://<ip>:8332``. A node saved as ``umbrel.local`` is the same node, so the scan
must show it as already connected instead of offering it as a new one to set up. The name is looked up through the event
loop's resolver; these tests replace that resolver with a table, so nothing here touches real DNS, the network or a node.
"""

from __future__ import annotations

import asyncio
import socket
from typing import Any

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

import bsmm.engine.discovery as discovery_mod

OUR_ADDRESS = "10.7.7.15"
NODE_IP = "10.7.7.6"
OTHER_IP = "10.7.7.5"
NODE_NAME = "umbrel.local"


class Refuser:
    """A fake node that answers every request with HTTP 401 and remembers that it was asked."""

    def __init__(self) -> None:
        self.requests = 0

    def app(self) -> Starlette:
        async def handler(request: Request) -> PlainTextResponse:
            self.requests += 1
            return PlainTextResponse("", status_code=401)

        return Starlette(routes=[Route("/", handler, methods=["POST"])])


class FakeTCP:
    def __init__(self) -> None:
        self.open: set[tuple[str, int]] = set()

    async def __call__(self, host: str, port: int, timeout: float = 1.0) -> bool:
        return (host, port) in self.open


class FakeResolver:
    """Stands in for the event loop's ``getaddrinfo``: names map to addresses, an exception, or ``"hang"``."""

    def __init__(self) -> None:
        self.names: dict[str, list[str] | Exception | str] = {}
        self.calls: list[str] = []

    async def lookup(self, host: str) -> list[tuple[Any, ...]]:
        self.calls.append(host)
        answer = self.names.get(host)
        if answer is None:
            raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")
        if isinstance(answer, Exception):
            raise answer
        if answer == "hang":
            await asyncio.Event().wait()
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0)) for ip in answer]


@pytest.fixture
def tcp(monkeypatch):
    fake = FakeTCP()
    monkeypatch.setattr(discovery_mod, "tcp_open", fake)
    monkeypatch.setattr(discovery_mod, "own_ipv4_addresses", set)
    monkeypatch.setattr("bsmm.sources.bitcoin_core.local_address_towards", lambda host: OUR_ADDRESS)
    return fake


@pytest.fixture
def resolver(monkeypatch):
    fake = FakeResolver()

    async def getaddrinfo(self: Any, host: str, port: Any, *, family: int = 0, type: int = 0, proto: int = 0, flags: int = 0) -> Any:
        return await fake.lookup(host)

    monkeypatch.setattr(asyncio.base_events.BaseEventLoop, "getaddrinfo", getaddrinfo)
    return fake


async def scan(ctx: Any, cidr: str = "10.7.7.0/29") -> Any:
    job = ctx.discovery.start([cidr])
    assert job._task is not None
    _, pending = await asyncio.wait({job._task}, timeout=20)
    assert not pending, f"scan still {job.status}"
    assert job.status == "finished", job.error
    return job


def node_of(job: Any, host: str) -> dict[str, Any]:
    return next(s for s in job.as_dict()["sources"] if s["url"] == f"http://{host}:8332")


async def save_node(ctx: Any, url: str, *, enabled: bool = True) -> None:
    await ctx.network.add_source("bitcoin_core", "My node", url, {"rpc_user": "umbrel"}, None, enabled=enabled)


async def test_a_node_saved_by_name_is_recognised_when_found_by_its_ip(api, tcp, resolver):
    _c, ctx, hosts = api
    saved = Refuser()
    hosts[NODE_IP] = saved.app()
    hosts[OTHER_IP] = Refuser().app()
    tcp.open.update({(NODE_IP, 8332), (OTHER_IP, 8332)})
    resolver.names[NODE_NAME] = [NODE_IP]
    await save_node(ctx, f"http://{NODE_NAME}")  # no port: it means 8332

    job = await scan(ctx)

    mine, other = node_of(job, NODE_IP), node_of(job, OTHER_IP)
    assert mine["already_configured"] is True and "refusal" not in mine and mine["needs_credentials"] is False
    assert saved.requests == 0  # a connected node is not even asked
    assert other["already_configured"] is False and other["refusal"]["reason"] == "needs_login"
    assert resolver.calls == [NODE_NAME]  # looked up once for the whole scan, not once per found node


async def test_a_node_saved_by_its_ip_is_recognised_without_any_lookup(api, tcp, resolver):
    _c, ctx, hosts = api
    saved = Refuser()
    hosts[NODE_IP] = saved.app()
    tcp.open.add((NODE_IP, 8332))
    await save_node(ctx, f"http://{NODE_IP}:8332")

    job = await scan(ctx)

    found = node_of(job, NODE_IP)
    assert found["already_configured"] is True and "refusal" not in found
    assert saved.requests == 0
    assert resolver.calls == []


async def test_a_saved_name_that_resolves_to_another_address_does_not_match(api, tcp, resolver):
    _c, ctx, hosts = api
    hosts[OTHER_IP] = Refuser().app()
    tcp.open.add((OTHER_IP, 8332))
    resolver.names[NODE_NAME] = [NODE_IP]
    await save_node(ctx, f"http://{NODE_NAME}")

    job = await scan(ctx)

    found = node_of(job, OTHER_IP)
    assert found["already_configured"] is False and found["refusal"]["reason"] == "needs_login"
    assert resolver.calls == [NODE_NAME]


async def test_a_switched_off_node_saved_by_name_does_not_count_and_is_not_looked_up(api, tcp, resolver):
    _c, ctx, hosts = api
    hosts[NODE_IP] = Refuser().app()
    tcp.open.add((NODE_IP, 8332))
    resolver.names[NODE_NAME] = [NODE_IP]
    await save_node(ctx, f"http://{NODE_NAME}", enabled=False)

    job = await scan(ctx)

    found = node_of(job, NODE_IP)
    assert found["already_configured"] is False and found["refusal"]["reason"] == "needs_login"
    assert resolver.calls == []  # a source that is switched off is never contacted


async def test_a_name_that_does_not_resolve_means_no_match_and_the_scan_still_finishes(api, tcp, resolver):
    _c, ctx, hosts = api
    hosts[NODE_IP] = Refuser().app()
    tcp.open.add((NODE_IP, 8332))
    await save_node(ctx, f"http://{NODE_NAME}")  # the table has no answer: the lookup fails like an unknown name

    job = await scan(ctx)

    found = node_of(job, NODE_IP)
    assert found["already_configured"] is False and found["refusal"]["reason"] == "needs_login"
    assert resolver.calls == [NODE_NAME]


async def test_a_name_lookup_that_never_answers_is_given_up_on(api, tcp, resolver):
    _c, ctx, hosts = api
    hosts[NODE_IP] = Refuser().app()
    tcp.open.add((NODE_IP, 8332))
    resolver.names[NODE_NAME] = "hang"
    await save_node(ctx, f"http://{NODE_NAME}")

    job = await scan(ctx)  # scan() fails the test if the scan does not finish within its own limit

    found = node_of(job, NODE_IP)
    assert found["already_configured"] is False and found["refusal"]["reason"] == "needs_login"
    assert resolver.calls == [NODE_NAME]


async def test_a_saved_name_the_resolver_rejects_outright_means_no_match_and_the_scan_still_finishes(api, tcp, resolver):
    _c, ctx, hosts = api
    hosts[NODE_IP] = Refuser().app()
    hosts[OTHER_IP] = Refuser().app()
    tcp.open.update({(NODE_IP, 8332), (OTHER_IP, 8332)})
    rejected_name = "umbrel..local"  # an empty label: the stdlib resolver refuses it before any lookup
    resolver.names[rejected_name] = UnicodeError("label empty or too long")
    resolver.names[NODE_NAME] = [NODE_IP]
    await save_node(ctx, f"http://{rejected_name}")
    await save_node(ctx, f"http://{NODE_NAME}")
    await save_node(ctx, f"http://{OTHER_IP}:8332")

    job = await scan(ctx)

    assert node_of(job, NODE_IP)["already_configured"] is True  # the other saved name still resolves
    assert node_of(job, OTHER_IP)["already_configured"] is True  # the literal saved address still matches
    assert sorted(resolver.calls) == sorted([rejected_name, NODE_NAME])
