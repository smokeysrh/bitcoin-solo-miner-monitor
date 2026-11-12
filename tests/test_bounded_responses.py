"""Replies from miners, pools, explorers and nodes are read with a size budget.

Every reader here gets a reply that is too big (streamed without end, declared too long, or small on the wire and large once
unpacked). Each must give up with its usual "bad response" error, read only a bounded part of the body and close the reply.
Normal replies, large or small, must still parse. The HTTP layer is ``httpx.MockTransport`` with streamed bodies, so the
test can see how much of a body was actually pulled.
"""

from __future__ import annotations

import gzip
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable, Iterator

import httpx
import pytest
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from bsmm.drivers.base import BadResponse
from bsmm.drivers.http import request_json
from bsmm.models import DeviceStatus, Source
from bsmm.sim.axeos import AxeOSSim
from bsmm.sources.base import SourceBadResponse, fetch_json
from bsmm.sources.bitcoin_core import BitcoinCoreSource, BitcoinRPC, probe_node_access

MIB = 1024 * 1024
CHUNK = b"x" * 65536
# Larger than any reply budget, so a reader that stops at its budget stays well under it.
PULL_CEILING = 10 * MIB
RUNAWAY_BODY = 40 * MIB  # more than any budget: the body a reader must not follow to the end
DECLARED_LENGTH = 64 * MIB
UNPACKED_SIZE = 16 * MIB  # larger than any budget once unpacked
JSON_HEADERS = {"content-type": "application/json"}


class Body(httpx.AsyncByteStream):
    """A streamed reply body that records how much of it the reader pulled and whether it was closed."""

    def __init__(self, chunks: Iterable[bytes]) -> None:
        self._chunks = iter(chunks)
        self.pulled = 0
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self._chunks:
            self.pulled += len(chunk)
            yield chunk

    async def aclose(self) -> None:
        self.closed = True


def runaway(total: int) -> Iterator[bytes]:
    """A valid JSON object whose one string value is ``total`` bytes long."""
    yield b'{"pad": "'
    sent = 0
    while sent < total:
        sent += len(CHUNK)
        yield CHUNK
    yield b'"}'


def normal_json(pad: int = 0) -> bytes:
    return b'{"result": 7, "pad": "' + b"x" * pad + b'"}'


def client_for(body: Body, *, status: int = 200, headers: dict[str, str] | None = None) -> httpx.AsyncClient:
    reply_headers = {**JSON_HEADERS, **(headers or {})}
    transport = httpx.MockTransport(lambda request: httpx.Response(status, headers=reply_headers, stream=body))
    return httpx.AsyncClient(transport=transport, timeout=5.0)


# Each reader makes one request through one of the three call paths and returns the value of ``result``.
Reader = Callable[[httpx.AsyncClient], Awaitable[object]]


async def read_as_driver(client: httpx.AsyncClient) -> object:
    data = await request_json(client, "GET", "http://miner.test/api/system/info", timeout=2.0)
    return data["result"]


async def read_as_source(client: httpx.AsyncClient) -> object:
    data = await fetch_json(client, "http://pool.test/api/pool", timeout=2.0)
    return data["result"]


async def read_as_node(client: httpx.AsyncClient) -> object:
    return await BitcoinRPC("http://node.test:8332", client, user="u", password="p").call("getblockcount")


READERS = [
    pytest.param(read_as_driver, BadResponse, id="miner-driver"),
    pytest.param(read_as_source, SourceBadResponse, id="pool-or-explorer-source"),
    pytest.param(read_as_node, SourceBadResponse, id="bitcoin-node-rpc"),
]


@pytest.mark.parametrize(("reader", "error"), READERS)
async def test_a_reply_that_keeps_streaming_is_cut_off_at_the_budget(reader: Reader, error: type[Exception]):
    body = Body(runaway(RUNAWAY_BODY))
    async with client_for(body) as client:
        with pytest.raises(error):
            await reader(client)
    assert body.pulled <= PULL_CEILING
    assert body.closed


@pytest.mark.parametrize(("reader", "error"), READERS)
async def test_a_reply_that_declares_too_long_a_body_is_refused_before_reading_it(reader: Reader, error: type[Exception]):
    body = Body([normal_json()])
    async with client_for(body, headers={"content-length": str(DECLARED_LENGTH)}) as client:
        with pytest.raises(error):
            await reader(client)
    assert body.pulled == 0
    assert body.closed


@pytest.mark.parametrize(("reader", "error"), READERS)
async def test_a_small_compressed_reply_that_unpacks_past_the_budget_is_refused(reader: Reader, error: type[Exception]):
    packed = gzip.compress(normal_json(UNPACKED_SIZE))
    assert len(packed) < MIB  # small on the wire
    body = Body([packed])
    async with client_for(body, headers={"content-encoding": "gzip"}) as client:
        with pytest.raises(error):
            await reader(client)
    assert body.closed


@pytest.mark.parametrize("encoding", [None, "gzip"])
@pytest.mark.parametrize("pad", [0, MIB])
@pytest.mark.parametrize("reader", [pytest.param(r.values[0], id=r.id) for r in READERS])
async def test_replies_inside_the_budget_still_parse(reader: Reader, pad: int, encoding: str | None):
    raw = normal_json(pad)
    wire = gzip.compress(raw) if encoding else raw
    body = Body([wire[i : i + 65536] for i in range(0, len(wire), 65536)])
    async with client_for(body, headers={"content-encoding": encoding} if encoding else None) as client:
        assert await reader(client) == 7


async def test_a_node_that_sends_an_oversized_reply_is_reported_unreachable_and_polling_goes_on():
    body = Body(runaway(RUNAWAY_BODY))
    source = Source(id="s", kind="bitcoin_core", name="node", url="http://node.test:8332")
    async with client_for(body) as client:
        status = await BitcoinCoreSource(source, {"rpc_user": "u", "rpc_password": "p"}, client).node()
    assert status is not None and status.reachable is False and status.error
    assert body.pulled <= PULL_CEILING


@pytest.mark.parametrize(("status", "reason"), [(200, None), (401, "needs_login")])
async def test_the_node_access_check_never_downloads_the_reply_body(status: int, reason: str | None):
    body = Body(runaway(RUNAWAY_BODY))
    async with client_for(body, status=status) as client:
        refusal = await probe_node_access(client, "http://node.test:8332")
    assert (refusal.reason if refusal else None) == reason
    assert body.pulled == 0


# -- one failed poll, then polling goes on -------------------------------------------------------------------------------------


def padded(app: ASGIApp, padding: dict[str, int]) -> ASGIApp:
    """Wrap an ASGI app so every body gets ``padding['extra']`` trailing spaces (still valid JSON) and a matching length."""

    async def wrapped(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await app(scope, receive, send)
            return
        start: Message = {}
        parts: list[bytes] = []

        async def capture(message: Message) -> None:
            if message["type"] == "http.response.start":
                start.update(message)
            elif message["type"] == "http.response.body":
                parts.append(message.get("body", b""))

        await app(scope, receive, capture)
        data = b"".join(parts) + b" " * padding["extra"]
        headers = [(k, v) for k, v in start["headers"] if k.lower() != b"content-length"]
        headers.append((b"content-length", str(len(data)).encode()))
        await send({**start, "headers": headers})
        await send({"type": "http.response.body", "body": data})

    return wrapped


async def test_an_oversized_miner_reply_is_one_failed_poll_and_the_next_poll_recovers(lan):
    ctx, hosts = lan
    padding = {"extra": 0}
    hosts["g.test"] = padded(AxeOSSim("gamma", seed=2, mac="AA:BB:CC:00:00:22").app(), padding)
    res = await ctx.fleet.add_by_host("g.test", drivers=["axeos"], name="G")
    rt = ctx.fleet.runtimes[res.device.id]
    await ctx.fleet._poll_once(rt)
    assert rt.failures == 0 and rt.status == DeviceStatus.ONLINE

    padding["extra"] = 3 * MIB  # the same valid reading, followed by more than any reply budget allows
    await ctx.fleet._poll_once(rt)
    assert rt.failures == 1 and rt.last_error
    assert rt.status == DeviceStatus.ONLINE  # one failed poll is tolerated like any other

    padding["extra"] = 0
    await ctx.fleet._poll_once(rt)
    assert rt.failures == 0 and rt.last_error is None and rt.status == DeviceStatus.ONLINE
