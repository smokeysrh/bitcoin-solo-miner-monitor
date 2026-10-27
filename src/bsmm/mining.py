"""Solo-mining math.

Everything here is pure (no I/O) so it is trivially testable and can be reused by the API, the CLI
and the MCP tools. The model is the textbook one:

* A miner doing ``H`` hashes/second against difficulty ``D`` finds blocks as a Poisson process with
  rate ``lambda = H / (D * 2**32)`` per second (precisely ``D * 2**48 / 0xFFFF`` hashes per block).
* P(at least one block within t seconds) = ``1 - exp(-lambda * t)``.
* Expected wait is ``1 / lambda``; the median wait is ``ln(2) / lambda``.

Luck does not accumulate: the odds of the *next* hash are the same no matter how long you have been
mining. The "work done" figures below are for context, not a promise.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

#: Expected number of hashes needed to meet difficulty 1 (exactly 2**48 / 0xFFFF, about 2**32).
HASHES_PER_DIFF1: float = 2**48 / 0xFFFF
BLOCKS_PER_EPOCH = 2016
HALVING_INTERVAL = 210_000
TARGET_BLOCK_SECONDS = 600
SATS_PER_BTC = 100_000_000
SECONDS_PER_DAY = 86_400
SECONDS_PER_YEAR = 365.25 * SECONDS_PER_DAY
#: Look-ahead windows (seconds) used for the "odds over time" table.
HORIZONS: dict[str, float] = {
    "hour": 3_600,
    "day": SECONDS_PER_DAY,
    "week": 7 * SECONDS_PER_DAY,
    "month": SECONDS_PER_YEAR / 12,
    "year": SECONDS_PER_YEAR,
    "five_years": 5 * SECONDS_PER_YEAR,
    "ten_years": 10 * SECONDS_PER_YEAR,
}


def hashes_per_block(difficulty: float) -> float:
    """Expected hashes needed to find one block at ``difficulty``."""
    return difficulty * HASHES_PER_DIFF1


def network_hashrate_from_difficulty(difficulty: float, block_seconds: float = TARGET_BLOCK_SECONDS) -> float:
    """Hashrate the network needs to sustain ``difficulty`` at the target block time."""
    return hashes_per_block(difficulty) / block_seconds


def block_rate(hashrate: float, difficulty: float) -> float:
    """Expected blocks per second for a miner at ``hashrate`` (H/s)."""
    if hashrate <= 0 or difficulty <= 0:
        return 0.0
    return hashrate / hashes_per_block(difficulty)


def probability_within(
    hashrate: float,
    difficulty: float,
    seconds: float,
    difficulty_growth_per_year: float = 0.0,
) -> float:
    """P(find >= 1 block within ``seconds``).

    ``difficulty_growth_per_year`` (0.3 = +30%/yr) models a rising network: the rate then decays
    exponentially and the cumulative hazard is integrated in closed form.
    """
    lam = block_rate(hashrate, difficulty)
    if lam <= 0 or seconds <= 0:
        return 0.0
    if difficulty_growth_per_year > -1 and difficulty_growth_per_year != 0:
        g = math.log1p(difficulty_growth_per_year) / SECONDS_PER_YEAR  # per second
        hazard = lam * (-math.expm1(-g * seconds)) / g
    else:
        hazard = lam * seconds
    return -math.expm1(-hazard)


def expected_seconds(hashrate: float, difficulty: float) -> float | None:
    """Mean time to a block. ``None`` when there is no hashrate."""
    lam = block_rate(hashrate, difficulty)
    return 1.0 / lam if lam > 0 else None


def median_seconds(hashrate: float, difficulty: float) -> float | None:
    lam = block_rate(hashrate, difficulty)
    return math.log(2) / lam if lam > 0 else None


def one_in(probability: float) -> float | None:
    return 1.0 / probability if probability > 0 else None


def work_to_expected_blocks(hashes: float, difficulty: float) -> float:
    """How many 'expected blocks' of work ``hashes`` represents at ``difficulty``."""
    if difficulty <= 0 or hashes <= 0:
        return 0.0
    return hashes / hashes_per_block(difficulty)


def chance_of_block_by_now(expected_blocks_of_work: float) -> float:
    """P(would already have found >= 1 block) after doing ``expected_blocks_of_work`` of work."""
    return -math.expm1(-max(0.0, expected_blocks_of_work))


def best_share_progress(best_diff: float | None, network_difficulty: float | None) -> float | None:
    """Fraction of the way a best share got to a block (1.0 would have been a block)."""
    if not best_diff or not network_difficulty or network_difficulty <= 0:
        return None
    return best_diff / network_difficulty


# --- chain schedule ------------------------------------------------------------------------------


def subsidy_sats(height: int) -> int:
    """Block subsidy in satoshis at ``height``."""
    halvings = height // HALVING_INTERVAL
    if halvings >= 64:
        return 0
    return (50 * SATS_PER_BTC) >> halvings


@dataclass(slots=True)
class HalvingInfo:
    height: int
    next_halving_height: int
    blocks_remaining: int
    seconds_remaining: float
    estimated_date: datetime
    subsidy_now_btc: float
    subsidy_next_btc: float
    progress: float  # 0..1 through the current halving era

    def as_dict(self) -> dict[str, Any]:
        return {
            "height": self.height,
            "next_halving_height": self.next_halving_height,
            "blocks_remaining": self.blocks_remaining,
            "seconds_remaining": self.seconds_remaining,
            "estimated_date": self.estimated_date.isoformat(),
            "subsidy_now_btc": self.subsidy_now_btc,
            "subsidy_next_btc": self.subsidy_next_btc,
            "progress": self.progress,
        }


def halving_info(height: int, now: datetime | None = None, block_seconds: float = TARGET_BLOCK_SECONDS) -> HalvingInfo:
    now = now or datetime.now(UTC)
    era = height // HALVING_INTERVAL
    nxt = (era + 1) * HALVING_INTERVAL
    remaining = nxt - height
    secs = remaining * block_seconds
    return HalvingInfo(
        height=height,
        next_halving_height=nxt,
        blocks_remaining=remaining,
        seconds_remaining=secs,
        estimated_date=now + timedelta(seconds=secs),
        subsidy_now_btc=subsidy_sats(height) / SATS_PER_BTC,
        subsidy_next_btc=subsidy_sats(nxt) / SATS_PER_BTC,
        progress=(height % HALVING_INTERVAL) / HALVING_INTERVAL,
    )


@dataclass(slots=True)
class EpochInfo:
    height: int
    epoch_start_height: int
    next_retarget_height: int
    blocks_into_epoch: int
    blocks_remaining: int
    progress: float  # 0..1
    seconds_remaining: float | None = None
    estimated_date: datetime | None = None
    estimated_change_pct: float | None = None  # +1.86 means difficulty rises 1.86%

    def as_dict(self) -> dict[str, Any]:
        return {
            "height": self.height,
            "epoch_start_height": self.epoch_start_height,
            "next_retarget_height": self.next_retarget_height,
            "blocks_into_epoch": self.blocks_into_epoch,
            "blocks_remaining": self.blocks_remaining,
            "progress": self.progress,
            "seconds_remaining": self.seconds_remaining,
            "estimated_date": self.estimated_date.isoformat() if self.estimated_date else None,
            "estimated_change_pct": self.estimated_change_pct,
        }


def epoch_info(
    height: int,
    epoch_start_time: float | None = None,
    tip_time: float | None = None,
    now: datetime | None = None,
) -> EpochInfo:
    """Where we are in the 2016-block difficulty epoch.

    When the timestamps of the epoch's first block and the current tip are known, the next
    adjustment (before Bitcoin's 4x clamp) is estimated like Bitcoin Core does it:
    ``expected_time / actual_time``.
    """
    now = now or datetime.now(UTC)
    into = height % BLOCKS_PER_EPOCH
    start = height - into
    remaining = BLOCKS_PER_EPOCH - into
    info = EpochInfo(
        height=height,
        epoch_start_height=start,
        next_retarget_height=start + BLOCKS_PER_EPOCH,
        blocks_into_epoch=into,
        blocks_remaining=remaining,
        progress=into / BLOCKS_PER_EPOCH,
    )
    if epoch_start_time is not None and tip_time is not None and into > 0 and tip_time > epoch_start_time:
        actual = tip_time - epoch_start_time
        expected = into * TARGET_BLOCK_SECONDS
        ratio = clamp_ratio(expected / actual)
        info.estimated_change_pct = (ratio - 1.0) * 100.0
        pace = actual / into  # seconds per block so far in this epoch
        info.seconds_remaining = remaining * pace
        info.estimated_date = now + timedelta(seconds=info.seconds_remaining)
    else:
        info.seconds_remaining = remaining * TARGET_BLOCK_SECONDS
        info.estimated_date = now + timedelta(seconds=info.seconds_remaining)
    return info


def clamp_ratio(r: float) -> float:
    """Bitcoin never moves difficulty by more than 4x up or down in one step."""
    return max(0.25, min(4.0, r))


# --- money ---------------------------------------------------------------------------------------


def energy_kwh(power_w: float, hours: float) -> float:
    return max(0.0, power_w) / 1000.0 * hours


def energy_cost(power_w: float, price_per_kwh: float, hours: float) -> float:
    return energy_kwh(power_w, hours) * max(0.0, price_per_kwh)


@dataclass(slots=True)
class Economics:
    price_per_kwh: float
    btc_price: float | None
    cost_per_day: float
    cost_per_month: float
    cost_per_year: float
    block_reward_btc: float
    expected_value_per_day: float | None
    expected_value_per_year: float | None
    #: expected value divided by electricity spend; 1.0 is break-even *in expectation*
    ev_to_cost_ratio: float | None
    #: price (USD) BTC would need for expected value to cover electricity
    break_even_btc_price: float | None

    def as_dict(self) -> dict[str, Any]:
        return {f: getattr(self, f) for f in self.__dataclass_fields__}


def economics(
    power_w: float,
    hashrate: float,
    difficulty: float,
    price_per_kwh: float,
    btc_price: float | None,
    block_reward_btc: float,
) -> Economics:
    cost_day = energy_cost(power_w, price_per_kwh, 24)
    rate_day = block_rate(hashrate, difficulty) * SECONDS_PER_DAY
    ev_day: float | None = None
    ev_year: float | None = None
    ratio: float | None = None
    break_even: float | None = None
    if btc_price is not None and btc_price > 0:
        ev_day = rate_day * block_reward_btc * btc_price
        ev_year = ev_day * (SECONDS_PER_YEAR / SECONDS_PER_DAY)
        ratio = (ev_day / cost_day) if cost_day > 0 else None
    if rate_day > 0 and block_reward_btc > 0 and cost_day > 0:
        break_even = cost_day / (rate_day * block_reward_btc)
    return Economics(
        price_per_kwh=price_per_kwh,
        btc_price=btc_price,
        cost_per_day=cost_day,
        cost_per_month=cost_day * 30.4375,
        cost_per_year=cost_day * 365.25,
        block_reward_btc=block_reward_btc,
        expected_value_per_day=ev_day,
        expected_value_per_year=ev_year,
        ev_to_cost_ratio=ratio,
        break_even_btc_price=break_even,
    )


# --- the combined report ---------------------------------------------------------------------------


@dataclass(slots=True)
class Horizon:
    name: str
    seconds: float
    probability: float
    one_in: float | None


@dataclass(slots=True)
class OddsReport:
    hashrate: float
    difficulty: float
    network_hashrate: float
    share_of_network: float
    blocks_per_day: float
    expected_seconds: float | None
    median_seconds: float | None
    horizons: list[Horizon] = field(default_factory=list)
    difficulty_growth_per_year: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "hashrate": self.hashrate,
            "difficulty": self.difficulty,
            "network_hashrate": self.network_hashrate,
            "share_of_network": self.share_of_network,
            "blocks_per_day": self.blocks_per_day,
            "expected_seconds": self.expected_seconds,
            "median_seconds": self.median_seconds,
            "difficulty_growth_per_year": self.difficulty_growth_per_year,
            "horizons": {
                h.name: {"seconds": h.seconds, "probability": h.probability, "one_in": h.one_in}
                for h in self.horizons
            },
        }


def odds_report(
    hashrate: float,
    difficulty: float,
    network_hashrate: float | None = None,
    difficulty_growth_per_year: float = 0.0,
) -> OddsReport:
    net = network_hashrate if network_hashrate and network_hashrate > 0 else network_hashrate_from_difficulty(difficulty)
    horizons = []
    for name, secs in HORIZONS.items():
        p = probability_within(hashrate, difficulty, secs, difficulty_growth_per_year)
        horizons.append(Horizon(name, secs, p, one_in(p)))
    return OddsReport(
        hashrate=hashrate,
        difficulty=difficulty,
        network_hashrate=net,
        share_of_network=(hashrate / net) if net > 0 else 0.0,
        blocks_per_day=block_rate(hashrate, difficulty) * SECONDS_PER_DAY,
        expected_seconds=expected_seconds(hashrate, difficulty),
        median_seconds=median_seconds(hashrate, difficulty),
        horizons=horizons,
        difficulty_growth_per_year=difficulty_growth_per_year,
    )
