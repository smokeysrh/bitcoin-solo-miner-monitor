"""API/MCP legacy disclosure and producer/consumer startup boundary regressions."""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bsmm.api.app import create_app
from bsmm.mcp_server import AsgiBackend, build_server
from bsmm.models import Device


@pytest.mark.parametrize("consumer", ["api", "mcp"])
@pytest.mark.parametrize("legacy", [True, False])
async def test_eng08_device_history_preserves_warning_and_flat_series(api, monkeypatch, consumer, legacy):
    client, ctx, _ = api
    device = Device(id="history-device", name="Synthetic", driver="sim", family="sim", model="sim", host="127.0.0.1", port=1)
    await ctx.store.save_device(device)
    ctx.fleet._spawn(device)
    rows = [{"device_id": device.id, "bucket": 3600, "n": 6, "hashrate_hs": 100},
            {"device_id": device.id, "bucket": 3660, "n": 1, "hashrate_hs": 200}]
    if not legacy:
        for row in rows:
            row["hashrate_hs_n"] = row["n"]
    await ctx.store.samples.insert_rollup_rows("samples_1m", rows)
    before = [dict(row) for row in await ctx.store.db.fetchall("SELECT * FROM samples_1m ORDER BY bucket")]
    # Freeze only the API window clock, not the store or adapter. MCP uses the real range route.
    monkeypatch.setattr("bsmm.api.util.time", SimpleNamespace(time=lambda: 3720))
    params: dict[str, str | int] = {"range": "2m", "metrics": "hashrate_hs"}
    if consumer == "api":
        params["step"] = 120
    fleet_response = await client.get("/api/v1/fleet/history", params=params)
    assert fleet_response.status_code == 200
    fleet = fleet_response.json()
    if consumer == "api":
        response = await client.get(f"/api/v1/devices/{device.id}/history", params=params)
        assert response.status_code == 200
        result = response.json()
        assert result["step"] == 120
        assert result["t"] == [3600, 3720]
        assert result["series"]["hashrate_hs"] == [pytest.approx(800 / 7), None]
    else:
        backend = AsgiBackend(create_app(ctx=ctx))
        server = build_server(backend)
        try:
            tool_result = await server.call_tool("get_history", {**params, "miner_id": device.id})
            payload = tool_result.model_dump()
            assert payload["is_error"] is False
            result = json.loads(payload["content"][0]["text"])
        finally:
            await backend.client.aclose()
    assert result["source"] == "samples_1m"
    assert "devices" not in result
    assert any(value is not None for value in result["series"]["hashrate_hs"])
    for key in ("step", "source", "t", "series"):
        assert result[key] == fleet[key]
    if legacy:
        assert fleet["warnings"]
        assert result.get("warnings") == fleet["warnings"]
    else:
        assert "warnings" not in result
    assert [dict(row) for row in await ctx.store.db.fetchall("SELECT * FROM samples_1m ORDER BY bucket")] == before


async def wait_for_cursor(store, event_id):
    async with asyncio.timeout(3):
        while await store.kv_get("alerts.event_cursor", 0) < event_id:
            await asyncio.sleep(0.005)


@pytest.mark.parametrize("cursor", [None, 0, 1])
@pytest.mark.parametrize("producer", ["fleet", "network"])
async def test_eng15_startup_baseline_preserves_new_events_and_existing_cursor(lan, monkeypatch, cursor, producer):
    ctx, _ = lan
    historical = await ctx.events.emit("block_found", "Historical event")
    catchup = await ctx.events.emit("block_found", "Retained catchup event")
    assert historical.id == 1
    if cursor is not None:
        await ctx.store.kv_set("alerts.event_cursor", cursor)
    dispatch = AsyncMock(return_value=[])
    monkeypatch.setattr(ctx.notifier, "dispatch", dispatch)
    emitted = asyncio.Event()
    release_consumer = asyncio.Event()
    fleet_ready = asyncio.Event()
    startup = None
    baseline_at_producer = None
    original_loop = ctx.alerts._event_loop
    original_tick = ctx.alerts.tick

    async def held_consumer():
        # Order-neutral: do not require defaults/baseline preparation to await a producer.
        await release_consumer.wait()
        await original_loop()

    async def checked_tick(now):
        assert fleet_ready.is_set(), "evaluation must not run before fleet initialization"
        await original_tick(now)

    async def emit_startup():
        nonlocal startup, baseline_at_producer
        baseline_at_producer = await ctx.store.kv_get("alerts.event_cursor")
        startup = await ctx.events.emit("block_found", "Startup event")
        emitted.set()

    async def fleet_start():
        if producer == "fleet":
            await emit_startup()
        fleet_ready.set()

    async def network_loop():
        if producer == "network":
            await emit_startup()
        await asyncio.Event().wait()

    monkeypatch.setattr(ctx.fleet, "start", fleet_start)
    monkeypatch.setattr(ctx.network, "_loop", network_loop)
    monkeypatch.setattr(ctx.alerts, "_event_loop", held_consumer)
    monkeypatch.setattr(ctx.alerts, "tick", checked_tick)
    try:
        await ctx.start()
        await asyncio.wait_for(emitted.wait(), 3)
        assert startup is not None
        release_consumer.set()
        await wait_for_cursor(ctx.store, startup.id)
        later = await ctx.events.emit("block_found", "Later event")
        await wait_for_cursor(ctx.store, later.id)
        titles = [call.args[0].title for call in dispatch.await_args_list]
        expected = ([] if cursor is None else ["Retained catchup event"])
        if cursor == 0:
            expected.insert(0, "Historical event")
        expected += ["Startup event", "Later event"]
        assert titles == expected
        assert baseline_at_producer == (catchup.id if cursor is None else cursor)
        receipt = await ctx.store.kv_get("alerts.event_rule:rule_block_found:x")
        assert receipt["event_id"] == later.id
        # Restart the real consumer with its durable cursor/receipt: no duplicate attempt.
        await ctx.alerts.stop()
        await ctx.alerts.start()
        final = await ctx.events.emit("block_found", "After restart")
        await wait_for_cursor(ctx.store, final.id)
        assert [call.args[0].title for call in dispatch.await_args_list] == [*expected, "After restart"]
    finally:
        for task in ctx._bg:
            task.cancel()
        await asyncio.gather(*ctx._bg, return_exceptions=True)
        await ctx.alerts.stop()
        await ctx.network.stop()
