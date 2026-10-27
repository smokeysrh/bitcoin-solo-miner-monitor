"""Shared test helpers: simulated miners reachable by fake hostnames, no real sockets needed."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest

from bsmm.config import RuntimeConfig
from bsmm.context import AppContext
from bsmm.sim.axeos import AxeOSSim


class MultiHostTransport(httpx.AsyncBaseTransport):
    """Routes requests by host name to in-process ASGI apps. ``hosts`` may be changed while running
    (that is how tests make a miner "disappear" and come back)."""

    def __init__(self, hosts: dict[str, object]) -> None:
        self.hosts = hosts
        self._cache: dict[str, httpx.ASGITransport] = {}

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host
        app = self.hosts.get(host)
        if app is None:
            self._cache.pop(host, None)
            raise httpx.ConnectError(f"no route to host {host}", request=request)
        if host not in self._cache:
            self._cache[host] = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
        return await self._cache[host].handle_async_request(request)


def make_client(hosts: dict[str, AxeOSSim]) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=MultiHostTransport({h: s.app() for h, s in hosts.items()}),
        headers={"Connection": "close"},
        timeout=5.0,
    )


@pytest.fixture
def gamma() -> AxeOSSim:
    return AxeOSSim("gamma", seed=1, mac="AA:BB:CC:00:00:11", hostname="sim-gamma")


@pytest.fixture
async def client(gamma: AxeOSSim):
    c = make_client({"gamma.test": gamma})
    yield c
    await c.aclose()


@pytest.fixture
async def api(lan):
    """(HTTP client for the API app, AppContext, simulated-miner hosts). Background tasks are not started;
    tests drive polling explicitly so they stay fast and deterministic."""
    from bsmm.api.app import create_app

    ctx, hosts = lan
    app = create_app(ctx=ctx)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://bsmm.test") as c:
        yield c, ctx, hosts


@pytest.fixture
async def lan(tmp_path) -> AsyncIterator[tuple[AppContext, dict[str, object]]]:
    """An AppContext (in-memory DB, no background tasks started) whose HTTP client talks to ``hosts``."""
    hosts: dict[str, object] = {}
    http = httpx.AsyncClient(transport=MultiHostTransport(hosts), headers={"Connection": "close"}, timeout=5.0)
    cfg = RuntimeConfig(data_dir=tmp_path, offline=True)
    ctx = await AppContext.create(cfg, http=http)
    yield ctx, hosts
    await ctx.fleet.stop()
    await ctx.http.aclose()
    await ctx.store.close()
