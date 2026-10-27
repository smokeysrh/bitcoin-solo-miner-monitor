import math
from datetime import UTC, datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st

from bsmm import mining as m

# Real values observed on the LAN node (Public Pool /api/network) on 2026-10-19.
DIFF = 140_577_680_051_919.6
NET_HASHRATE = 1.080971700496754e21
FLEET = 12.063058939714703e12  # sum of two miners, H/s


def test_hashes_per_diff1_is_about_2_pow_32():
    assert pytest.approx(2**32, rel=2e-5) == m.HASHES_PER_DIFF1
    assert pytest.approx(4295032833.0000153) == m.HASHES_PER_DIFF1


def test_network_hashrate_matches_reported():
    # Difficulty-derived hashrate should land within 10% of what the node reports.
    derived = m.network_hashrate_from_difficulty(DIFF)
    assert derived == pytest.approx(NET_HASHRATE, rel=0.10)


def test_block_rate_formula():
    expected = FLEET / (DIFF * 2**32)
    assert m.block_rate(FLEET, DIFF) == pytest.approx(expected, rel=2e-5)


def test_daily_probability_and_one_in():
    p_day = m.probability_within(FLEET, DIFF, m.SECONDS_PER_DAY)
    # about 1.7e-6 per day for a ~12 TH/s fleet
    assert 1.5e-6 < p_day < 1.9e-6
    p_year = m.probability_within(FLEET, DIFF, m.SECONDS_PER_YEAR)
    assert 1 / 1900 < p_year < 1 / 1500  # roughly "1 in 1,700 per year"
    assert m.one_in(p_year) == pytest.approx(1 / p_year)


def test_expected_and_median_time():
    exp = m.expected_seconds(FLEET, DIFF)
    med = m.median_seconds(FLEET, DIFF)
    assert exp is not None and med is not None
    assert med == pytest.approx(exp * math.log(2))
    years = exp / m.SECONDS_PER_YEAR
    assert 1_500 < years < 1_900


def test_zero_hashrate_is_safe():
    assert m.block_rate(0, DIFF) == 0
    assert m.expected_seconds(0, DIFF) is None
    assert m.probability_within(0, DIFF, 1e9) == 0
    assert m.probability_within(FLEET, 0, 1e9) == 0
    assert m.one_in(0) is None


def test_difficulty_growth_lowers_long_horizon_odds_only():
    base = m.probability_within(FLEET, DIFF, 10 * m.SECONDS_PER_YEAR)
    grown = m.probability_within(FLEET, DIFF, 10 * m.SECONDS_PER_YEAR, difficulty_growth_per_year=0.4)
    assert 0 < grown < base
    short_base = m.probability_within(FLEET, DIFF, 3600)
    short_grown = m.probability_within(FLEET, DIFF, 3600, difficulty_growth_per_year=0.4)
    assert short_grown == pytest.approx(short_base, rel=1e-3)


@given(
    h=st.floats(min_value=1e6, max_value=1e24),
    d=st.floats(min_value=1e9, max_value=1e18),
    t=st.floats(min_value=1, max_value=1e10),
)
def test_probability_is_a_probability_and_monotonic(h, d, t):
    p1 = m.probability_within(h, d, t)
    p2 = m.probability_within(h, d, t * 2)
    assert 0.0 <= p1 <= 1.0
    assert p1 <= p2 <= 1.0


def test_subsidy_schedule():
    assert m.subsidy_sats(0) == 50 * m.SATS_PER_BTC
    assert m.subsidy_sats(209_999) == 50 * m.SATS_PER_BTC
    assert m.subsidy_sats(210_000) == 25 * m.SATS_PER_BTC
    assert m.subsidy_sats(840_000) == 3_12_500_000
    assert m.subsidy_sats(972_174) == 312_500_000
    assert m.subsidy_sats(1_050_000) == 156_250_000
    assert m.subsidy_sats(64 * m.HALVING_INTERVAL) == 0


def test_halving_info():
    now = datetime(2026, 10, 19, tzinfo=UTC)
    h = m.halving_info(972_174, now=now)
    assert h.next_halving_height == 1_050_000
    assert h.blocks_remaining == 77_826
    assert h.subsidy_now_btc == 3.125
    assert h.subsidy_next_btc == 1.5625
    assert h.seconds_remaining == 77_826 * 600
    assert 0.0 < h.progress < 1.0


def test_epoch_matches_mempool_space_numbers():
    # mempool.space on 2026-10-19: tip 972174 -> next retarget 973728, 1554 blocks to go, 22.9% through.
    e = m.epoch_info(972_174)
    assert e.next_retarget_height == 973_728
    assert e.blocks_remaining == 1_554
    assert e.blocks_into_epoch == 462
    assert e.progress == pytest.approx(0.22916, abs=1e-4)


def test_epoch_estimates_difficulty_change_from_timestamps():
    # 462 blocks mined in 10% less than 600 s each -> difficulty should rise about 11%
    e = m.epoch_info(972_174, epoch_start_time=0.0, tip_time=462 * 540.0)
    assert e.estimated_change_pct == pytest.approx((600 / 540 - 1) * 100, rel=1e-6)
    assert e.seconds_remaining == pytest.approx(1554 * 540)


def test_epoch_change_is_clamped_to_4x():
    e = m.epoch_info(972_174, epoch_start_time=0.0, tip_time=462 * 60.0)
    assert e.estimated_change_pct == pytest.approx(300.0)


def test_work_and_luck():
    one_block = m.hashes_per_block(DIFF)
    assert m.work_to_expected_blocks(one_block, DIFF) == pytest.approx(1.0)
    assert m.chance_of_block_by_now(1.0) == pytest.approx(1 - math.exp(-1))
    assert m.chance_of_block_by_now(0.0) == 0.0
    assert m.chance_of_block_by_now(-5) == 0.0


def test_best_share_progress():
    assert m.best_share_progress(122e9, DIFF) == pytest.approx(122e9 / DIFF)
    assert m.best_share_progress(None, DIFF) is None
    assert m.best_share_progress(1e9, 0) is None


def test_economics():
    eco = m.economics(
        power_w=240.0, hashrate=FLEET, difficulty=DIFF, price_per_kwh=0.12, btc_price=82_000.0, block_reward_btc=3.125
    )
    assert eco.cost_per_day == pytest.approx(240 / 1000 * 24 * 0.12)
    assert eco.cost_per_year == pytest.approx(eco.cost_per_day * 365.25)
    assert eco.expected_value_per_day is not None and eco.expected_value_per_day > 0
    assert eco.ev_to_cost_ratio is not None
    # break-even price is where EV == cost
    assert eco.break_even_btc_price is not None
    ev_at_break_even = m.block_rate(FLEET, DIFF) * m.SECONDS_PER_DAY * 3.125 * eco.break_even_btc_price
    assert ev_at_break_even == pytest.approx(eco.cost_per_day, rel=1e-9)


def test_economics_without_price_or_power():
    eco = m.economics(0.0, FLEET, DIFF, 0.12, None, 3.125)
    assert eco.cost_per_day == 0
    assert eco.expected_value_per_day is None
    assert eco.break_even_btc_price is None


def test_odds_report_shape():
    rep = m.odds_report(FLEET, DIFF, NET_HASHRATE)
    d = rep.as_dict()
    assert set(d["horizons"]) == set(m.HORIZONS)
    assert d["share_of_network"] == pytest.approx(FLEET / NET_HASHRATE)
    assert d["blocks_per_day"] == pytest.approx(m.block_rate(FLEET, DIFF) * 86400)
