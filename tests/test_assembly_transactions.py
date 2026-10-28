"""Composed monitoring writes retain the database owner's atomic boundary."""
import asyncio
from unittest.mock import AsyncMock

import pytest

from bsmm.models import Telemetry
from bsmm.storage.samples import telemetry_to_row


@pytest.mark.parametrize("rollback", [False, True])
async def test_counted_samples_and_alert_receipt_join_outer_transaction(lan, rollback):
    ctx, _ = lan
    rule = await ctx.alerts.create_rule({"kind": "block_found", "cooldown_s": 0})
    ctx.alerts.notifier.dispatch = AsyncMock(return_value=[])
    rows = [telemetry_to_row("fixture", Telemetry(ts=3600, hashrate_hs=100)),
            telemetry_to_row("fixture", Telemetry(ts=3610, hashrate_hs=None))]
    receipt = f"alerts.event_rule:{rule.id}:x"

    async def write_composed():
        async with ctx.store.db.tx():
            await ctx.store.samples.write(rows)
            await ctx.alerts.handle_event({"id": 1, "type": "block_found", "title": "fixture only"})
            await ctx.store.kv_set("alerts.event_cursor", 1)
            assert await ctx.store.db.scalar("SELECT hashrate_hs_n FROM samples_1h") == 1
            if rollback:
                raise RuntimeError("injected rollback")

    if rollback:
        with pytest.raises(RuntimeError, match="injected rollback"):
            await asyncio.wait_for(write_composed(), 2)
    else:
        await asyncio.wait_for(write_composed(), 2)
    ctx.alerts.notifier.dispatch.assert_awaited_once()
    assert await ctx.store.kv_get("alerts.event_cursor") == (None if rollback else 1)
    assert (await ctx.store.kv_get(receipt) is None) == rollback
    for table in ("samples", "samples_1m", "samples_1h", "samples_1d"):
        count = await ctx.store.db.scalar(f"SELECT COUNT(*) FROM {table}")
        assert count == (0 if rollback else (2 if table == "samples" else 1))


async def test_alert_receipt_cannot_commit_another_tasks_counted_samples(lan):
    ctx, _ = lan
    rule = await ctx.alerts.create_rule({"kind": "block_found", "cooldown_s": 0})
    ctx.alerts.notifier.dispatch = AsyncMock(return_value=[])
    entered, release, attempted = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def owner():
        with pytest.raises(RuntimeError, match="injected rollback"):
            async with ctx.store.db.tx():
                await ctx.store.samples.write([telemetry_to_row("fixture", Telemetry(ts=3600, hashrate_hs=100))])
                entered.set()
                await release.wait()
                raise RuntimeError("injected rollback")

    async def alert():
        await entered.wait()
        attempted.set()
        await ctx.alerts.handle_event({"id": 1, "type": "block_found", "title": "fixture only"})
        await ctx.store.kv_set("alerts.event_cursor", 1)

    first, second = asyncio.create_task(owner()), asyncio.create_task(alert())
    try:
        await asyncio.wait_for(attempted.wait(), 2)
        # SQLite barrier, not a competing commit. The alert must wait for ownership.
        await ctx.store.db.conn.execute("SELECT 1")
        assert not second.done()
    finally:
        release.set()
        await asyncio.wait_for(asyncio.gather(first, second), 2)
    assert await ctx.store.db.scalar("SELECT COUNT(*) FROM samples") == 0
    assert await ctx.store.db.scalar("SELECT COUNT(*) FROM samples_1h") == 0
    assert await ctx.store.kv_get("alerts.event_cursor") == 1
    assert (await ctx.store.kv_get(f"alerts.event_rule:{rule.id}:x"))["event_id"] == 1
    ctx.alerts.notifier.dispatch.assert_awaited_once()
