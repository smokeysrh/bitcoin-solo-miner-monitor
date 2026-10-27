"""Things ASGITransport cannot do: real streaming (SSE) and the MCP endpoint over the wire."""

import asyncio
import json

import httpx
import pytest
from mcp.client import Client
from mcp.client.streamable_http import streamable_http_client

from bsmm.api.app import create_app
from bsmm.sim.axeos import AxeOSSim

from .live import serve


async def _miner(ctx, hosts):
    hosts["gamma.test"] = AxeOSSim("gamma", seed=1, mac="AA:BB:CC:00:00:11").app()
    res = await ctx.fleet.add_by_host("gamma.test", drivers=["axeos"])
    await ctx.fleet._poll_once(ctx.fleet.runtimes[res.device.id])
    return res.device


async def test_sse_stream_delivers_hello_fleet_and_device_updates(lan):
    ctx, hosts = lan
    dev = await _miner(ctx, hosts)
    async with serve(create_app(ctx=ctx)) as base, httpx.AsyncClient(timeout=10) as c:
        events: list[str] = []
        async with c.stream("GET", f"{base}/api/v1/stream", params={"topics": "device,fleet"}) as r:
            assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
            async for line in r.aiter_lines():
                if line.startswith("event: "):
                    events.append(line[7:])
                if line == "event: fleet":
                    ctx.bus.publish("device", {"id": dev.id, "view": {"name": "x"}})
                if line.startswith("data:") and events and events[-1] == "device":
                    assert json.loads(line[5:])["id"] == dev.id
                    break
        assert events[:2] == ["hello", "fleet"] and events[-1] == "device"
        bad = await c.get(f"{base}/api/v1/stream", params={"topics": "bogus"})
        assert bad.status_code == 400


async def test_sse_requires_auth_when_a_password_is_set(lan):
    ctx, _ = lan
    await ctx.auth.set_password("correct horse battery")
    await ctx.settings.update({"auth": {"mode": "password"}})
    async with serve(create_app(ctx=ctx)) as base, httpx.AsyncClient(timeout=5) as c:
        assert (await c.get(f"{base}/api/v1/stream")).status_code == 401


async def test_mcp_tools_work_end_to_end(lan):
    ctx, hosts = lan
    dev = await _miner(ctx, hosts)
    async with serve(create_app(ctx=ctx)) as base, Client(f"{base}/mcp") as mcp:
        tools = {t.name for t in (await mcp.list_tools()).tools}
        assert {"get_overview", "list_miners", "scan_network", "restart_miner", "get_odds", "configure_source",
                "create_notification_channel", "run_bulk_action", "get_diagnostics"} <= tools
        res = await mcp.call_tool("list_miners", {})
        text = json.dumps(res.model_dump(mode="json"))
        assert dev.id in text and "Bitaxe Gamma" in text
        ov = await mcp.call_tool("get_overview", {})
        assert "hashrate_hs" in json.dumps(ov.model_dump(mode="json"))
        # a write that the safety layer should handle: bulk previews by default
        prev = await mcp.call_tool("run_bulk_action", {"action": "restart", "all_miners": True})
        assert '"dry_run": true' in json.dumps(prev.model_dump(mode="json")).replace("\\", "").replace('"dry_run":true', '"dry_run": true')
        # errors come back readable
        bad = await mcp.call_tool("get_miner", {"miner_id": "dev_nope"})
        assert bad.is_error and "was not found" in json.dumps(bad.model_dump(mode="json"))
        prompts = {p.name for p in (await mcp.list_prompts()).prompts}
        assert {"setup_my_miners", "mining_report"} <= prompts


async def test_mcp_endpoint_is_protected_like_the_rest_of_the_api(lan):
    ctx, hosts = lan
    await _miner(ctx, hosts)
    await ctx.auth.set_password("correct horse battery")
    await ctx.settings.update({"auth": {"mode": "password"}})
    _, token = await ctx.store.create_token("agent", "read")
    async with serve(create_app(ctx=ctx)) as base:
        async with httpx.AsyncClient() as c:
            r = await c.post(f"{base}/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "ping"})
            assert r.status_code == 401 and r.json()["error"]["code"] == "auth_required"
        import httpx2

        client = httpx2.AsyncClient(headers={"Authorization": f"Bearer {token}"}, timeout=30)
        async with client, streamable_http_client(f"{base}/mcp", http_client=client) as streams:
            from mcp.client import ClientSession

            async with ClientSession(*streams) as session:
                await session.initialize()
                ok = await session.call_tool("list_miners", {})
                assert not ok.is_error
                # the token only has `read` scope, so the control tools must be refused by the REST layer
                no = await session.call_tool("restart_miner", {"miner_id": next(iter(ctx.fleet.runtimes))})
                assert no.is_error and "scope" in json.dumps(no.model_dump(mode="json"))
    assert pytest is not None and asyncio is not None
