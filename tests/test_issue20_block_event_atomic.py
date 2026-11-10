"""Issue #20: a found block and its durable alert event are saved together.

A failure after the block row is inserted but before the event is stored must not leave a block
that a retry skips as a duplicate (which would mean the alert is never created).
"""
from __future__ import annotations

import time

import pytest

from bsmm.engine.network import NetworkState
from bsmm.models import Event
from bsmm.sources.base import BlockInfo

ADDR = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"


def _fail_first_event_write(ctx, monkeypatch) -> None:
    real_add_event = ctx.store.add_event
    calls = 0

    async def flaky(event: Event) -> Event:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("synthetic failure while storing the event")
        return await real_add_event(event)

    monkeypatch.setattr(ctx.store, "add_event", flaky)


def _drain(sub) -> list:
    out = []
    while not sub.queue.empty():
        msg = sub.queue.get_nowait()
        if msg is not None:
            out.append(msg)
    return out


async def test_retry_after_failed_event_write_keeps_one_block_and_one_event(lan, monkeypatch):
    ctx, _ = lan
    sub = ctx.bus.subscribe({"block_found"})
    block = BlockInfo(hash="ab" * 32, height=972_176, ts=time.time(), reward_sats=315_000_000)
    _fail_first_event_write(ctx, monkeypatch)

    with pytest.raises(RuntimeError, match="synthetic failure"):
        await ctx.network.record_block_found(block, ADDR, source="chain")
    assert await ctx.network.record_block_found(block, ADDR, source="chain") is True

    assert await ctx.store.db.scalar("SELECT COUNT(*) FROM blocks_found") == 1
    assert len(await ctx.store.list_events(types=["block_found"])) == 1
    assert len(_drain(sub)) == 1
    # A further report of the same block stays a no-op.
    assert await ctx.network.record_block_found(block, ADDR, source="chain") is False
    assert len(await ctx.store.list_events(types=["block_found"])) == 1
    sub.close()


async def test_block_check_retry_creates_the_event_after_a_failed_write(lan, monkeypatch):
    ctx, _ = lan
    net = ctx.network
    net.watch_addresses = lambda: [ADDR]
    await ctx.store.kv_set("blocks.last_checked", 100)
    net._last_height = 100
    state = NetworkState(
        height=101,
        recent_blocks=[BlockInfo(hash="cd" * 32, height=101, ts=time.time(), coinbase_addresses=[ADDR])],
    )
    _fail_first_event_write(ctx, monkeypatch)

    with pytest.raises(RuntimeError, match="synthetic failure"):
        await net._after_merge(state, 100, None)
    assert await ctx.store.kv_get("blocks.last_checked") == 100  # the height was not advanced
    await net._after_merge(state, 100, None)

    assert await ctx.store.db.scalar("SELECT COUNT(*) FROM blocks_found") == 1
    assert len(await ctx.store.list_events(types=["block_found"])) == 1
    assert await ctx.store.kv_get("blocks.last_checked") == 101
