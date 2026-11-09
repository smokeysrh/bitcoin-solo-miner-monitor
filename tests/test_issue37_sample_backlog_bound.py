"""Issue #37: a persistent storage failure must not let the in-memory sample backlog grow without limit.

A failed batch is still retained (see ``test_failed_rollup_retains_batch_and_retry_is_atomic``), but a long
outage may only keep a bounded number of rows, must say that it is degraded, and must recover afterwards.
Uses simulators and a temporary database only.
"""
import contextlib
import sqlite3

from bsmm.models import Telemetry
from bsmm.storage.samples import telemetry_to_row

from .test_foundation_fleet import miner

# A long outage's worth of rows (hours for a large fleet). Far above any sane in-memory bound.
OUTAGE_ROWS = 60_000
# The backlog after the outage must stay well below the flood. The exact cap is an implementation choice.
MAX_ACCEPTABLE_BACKLOG = 50_000
OLDEST_TS = 3600
POLLS_DURING_OUTAGE = 3


def _sample_status(diagnostics: dict) -> str:
    return next(c["status"] for c in diagnostics["checks"] if c["id"] == "samples")


async def test_sustained_write_failure_keeps_backlog_bounded_and_recovers(api, monkeypatch):
    client, ctx, hosts = api
    did, _ = await miner(ctx, hosts)
    original_write = ctx.store.samples.write

    async def failing_write(rows):
        raise sqlite3.OperationalError("simulated disk full")

    monkeypatch.setattr(ctx.store.samples, "write", failing_write)
    ctx.fleet._pending.extend(
        telemetry_to_row(did, Telemetry(ts=OLDEST_TS + i, hashrate_hs=100)) for i in range(OUTAGE_ROWS)
    )

    # Polling continues and the writer keeps retrying while storage stays broken.
    for _ in range(POLLS_DURING_OUTAGE):
        await ctx.fleet.poll_now(did)
        with contextlib.suppress(sqlite3.OperationalError):  # the writer loop logs this and retries
            await ctx.fleet._flush_samples()

    assert len(ctx.fleet._pending) <= MAX_ACCEPTABLE_BACKLOG
    assert _sample_status((await client.get("/api/v1/system/diagnostics")).json()) == "fail"

    # Storage comes back: the retained rows are written, the newest evidence is kept and the gap stays visible.
    monkeypatch.setattr(ctx.store.samples, "write", original_write)
    await ctx.fleet._flush_samples()
    assert not ctx.fleet._pending
    assert await ctx.store.db.scalar("SELECT COUNT(*) FROM samples WHERE ts = ?", (OLDEST_TS,)) == 0
    assert await ctx.store.db.scalar("SELECT COUNT(*) FROM samples WHERE ts > ?", (OLDEST_TS + OUTAGE_ROWS,)) >= 1
    assert _sample_status((await client.get("/api/v1/system/diagnostics")).json()) == "warn"
