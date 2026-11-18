"""Issue #160: the work counter credits time using each miner's own check interval.

The credited time between two readings is capped at 3x the interval the poll loop really uses for that miner
(its own ``poll_interval_s``, else the global interval, never below 5 s), so a slow-checked miner is not
undercounted while an outage gap is still not credited.
"""
import pytest

from bsmm import mining
from bsmm.models import Telemetry

from .test_foundation_fleet import miner

HASHRATE_HS = 1e12
GLOBAL_INTERVAL_S = 10.0
SLOW_INTERVAL_S = 300.0
FIRST_READING_TS = 1_000_000.0
DIFFICULTY = 1e14


async def setup_miner(ctx, hosts, poll_interval_s):
    """A miner (optionally with its own interval) and its runtime; the global interval is the default 10 s."""
    did, _ = await miner(ctx, hosts)
    assert ctx.settings.current.polling.interval_s == GLOBAL_INTERVAL_S
    if poll_interval_s is not None:
        await ctx.fleet.update(did, {"poll_interval_s": poll_interval_s})
    return ctx.fleet.runtimes[did]


def credited_hashes(ctx, rt, gap_s):
    """Hashes the fleet adds for a good reading ``gap_s`` seconds after the previous one."""
    before, _ = ctx.fleet.work
    prev = Telemetry(ts=FIRST_READING_TS, hashrate_hs=HASHRATE_HS)
    latest = Telemetry(ts=FIRST_READING_TS + gap_s, hashrate_hs=HASHRATE_HS)
    ctx.fleet._accumulate_work(rt, latest, prev, latest.ts)
    after, _ = ctx.fleet.work
    return after - before


async def test_slow_miner_is_credited_its_whole_check_interval(lan):
    ctx, hosts = lan
    rt = await setup_miner(ctx, hosts, SLOW_INTERVAL_S)
    assert credited_hashes(ctx, rt, SLOW_INTERVAL_S) == pytest.approx(HASHRATE_HS * SLOW_INTERVAL_S)


async def test_slow_miner_blocks_of_work_follow_the_credited_time(lan):
    ctx, hosts = lan
    rt = await setup_miner(ctx, hosts, SLOW_INTERVAL_S)
    ctx.fleet.difficulty_provider = lambda: DIFFICULTY
    credited_hashes(ctx, rt, SLOW_INTERVAL_S)
    _, blocks = ctx.fleet.work
    assert blocks == pytest.approx(mining.work_to_expected_blocks(HASHRATE_HS * SLOW_INTERVAL_S, DIFFICULTY))


async def test_slow_miner_outage_gap_is_still_capped_at_three_intervals(lan):
    ctx, hosts = lan
    rt = await setup_miner(ctx, hosts, SLOW_INTERVAL_S)
    gap_s = 10 * SLOW_INTERVAL_S
    assert credited_hashes(ctx, rt, gap_s) == pytest.approx(HASHRATE_HS * 3 * SLOW_INTERVAL_S)


async def test_miner_without_own_interval_keeps_the_global_cap(lan):
    ctx, hosts = lan
    rt = await setup_miner(ctx, hosts, None)
    assert credited_hashes(ctx, rt, 5 * GLOBAL_INTERVAL_S) == pytest.approx(HASHRATE_HS * 3 * GLOBAL_INTERVAL_S)


async def test_miner_without_own_interval_is_credited_a_normal_gap(lan):
    ctx, hosts = lan
    rt = await setup_miner(ctx, hosts, None)
    assert credited_hashes(ctx, rt, GLOBAL_INTERVAL_S) == pytest.approx(HASHRATE_HS * GLOBAL_INTERVAL_S)


async def test_fast_miner_cap_is_floored_at_five_seconds(lan):
    ctx, hosts = lan
    rt = await setup_miner(ctx, hosts, 2.0)  # the shortest interval a miner may have
    assert credited_hashes(ctx, rt, 100.0) == pytest.approx(HASHRATE_HS * 3 * 5.0)
