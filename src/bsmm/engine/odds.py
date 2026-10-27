"""Turn fleet hashrate + network state into the numbers solo miners care about.

Everything is derived from :mod:`bsmm.mining`; this module only gathers the inputs and phrases the
result in plain English (used by the dashboard, the CLI and the MCP tools).
"""

from __future__ import annotations

from typing import Any

from bsmm import mining
from bsmm.engine.network import NetworkState
from bsmm.models import FleetSummary
from bsmm.settings import Settings
from bsmm.units import format_duration, format_hashrate, format_odds, format_percent, format_si


def build_odds(
    summary: FleetSummary,
    net: NetworkState,
    settings: Settings,
    *,
    work_hashes: float = 0.0,
    expected_blocks_of_work: float = 0.0,
    blocks_found: int = 0,
    hashrate_hs: float | None = None,
    difficulty: float | None = None,
    power_w: float | None = None,
    growth: float | None = None,
) -> dict[str, Any]:
    """``hashrate_hs`` / ``difficulty`` / ``power_w`` override the live values for what-if questions."""
    hr = hashrate_hs if hashrate_hs is not None else summary.hashrate_hs
    diff = difficulty if difficulty is not None else net.difficulty
    if not diff:
        return {
            "available": False,
            "reason": "The network difficulty is not known yet. Add a Bitcoin node or pool in Settings, or allow public data (mempool.space).",
        }
    g = growth if growth is not None else settings.network.difficulty_growth_per_year
    report = mining.odds_report(hr, diff, net.network_hashrate_hs, g)
    out: dict[str, Any] = {"available": True, **report.as_dict()}
    out["live"] = hashrate_hs is None and difficulty is None

    # money
    power = power_w if power_w is not None else (summary.power_wall_w if summary.power_wall_w is not None else summary.power_w)
    reward = net.block_reward_btc if net.block_reward_btc is not None else (3.125 if net.height is None else mining.subsidy_sats(net.height) / 1e8)
    eco = mining.economics(power or 0.0, hr, diff, settings.energy.price_per_kwh, net.btc_price, reward)
    out["economics"] = eco.as_dict() | {"power_w": power, "currency": settings.units.currency}

    # progress / luck
    out["work"] = {
        "total_hashes": work_hashes,
        "expected_blocks_of_work": expected_blocks_of_work,
        "chance_found_by_now": mining.chance_of_block_by_now(expected_blocks_of_work),
        "blocks_found": blocks_found,
    }
    best = summary.best_diff
    out["best_share"] = {
        "difficulty": best,
        "progress_to_block": mining.best_share_progress(best, diff),
        "device_id": summary.best_diff_device_id,
    }

    year = report.horizons[4]
    day = report.horizons[1]
    out["plain_english"] = _sentences(hr, report, year.probability, day.probability, eco, out["best_share"], settings)
    return out


def _sentences(hr: float, rep: mining.OddsReport, p_year: float, p_day: float, eco: mining.Economics,
               best: dict[str, Any], settings: Settings) -> list[str]:
    if hr <= 0:
        return ["Nothing is hashing right now, so there are no odds to show."]
    lines = [
        f"At {format_hashrate(hr)} you hold about {format_percent(rep.share_of_network, 7)} of the network's hashrate.",
        f"Your chance of finding a block in a year is {format_odds(p_year)} ({format_percent(p_year, 4)}); "
        f"on average you would wait {format_duration(rep.expected_seconds)}.",
        "Every hash is an independent ticket: it doesn't matter how long you have been mining, the next one is just as likely to win as the first.",
    ]
    if best.get("progress_to_block"):
        lines.append(f"Your best share so far ({format_si(best['difficulty'])}) reached {format_percent(best['progress_to_block'], 4)} of the way to a block.")
    if eco.expected_value_per_year is not None and eco.cost_per_year > 0:
        cur = settings.units.currency
        lines.append(
            f"Electricity costs about {eco.cost_per_year:,.0f} {cur} a year; the expected value of the block lottery is about "
            f"{eco.expected_value_per_year:,.0f} {cur} a year (it pays out rarely and in one huge lump: treat it as a lottery ticket, not income)."
        )
    return lines
