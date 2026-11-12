"""Unknown power is not zero power: a miner that reports no power must not look free to run."""
import pytest

from bsmm import mining
from bsmm.engine.fleet import DeviceRuntime, build_summary
from bsmm.engine.network import NetworkState
from bsmm.engine.odds import build_odds
from bsmm.models import Device, DeviceStatus, FleetSummary, Telemetry
from bsmm.settings import Settings

COST_FIELDS = ("cost_per_day", "cost_per_month", "cost_per_year", "ev_to_cost_ratio")
NET = NetworkState(difficulty=1e14, btc_price=80_000.0)


def _runtime(name: str, power_w: float | None) -> DeviceRuntime:
    device = Device(id=name, name=name, driver="axeos", family="bitaxe", model="m", host=name, port=80)
    rt = DeviceRuntime(device=device, status=DeviceStatus.ONLINE, telemetry=Telemetry(hashrate_hs=1e12, power_w=power_w))
    rt.hashrate_smooth = 1e12
    return rt


def _daily_cost(power_w: float) -> float:
    return power_w / 1000.0 * 24 * Settings().energy.price_per_kwh


def test_economics_with_unknown_power_has_no_cost():
    eco = mining.economics(None, 1e12, 1e14, 0.12, 80_000.0, 3.125)
    for name in COST_FIELDS:
        assert getattr(eco, name) is None, name
    assert eco.expected_value_per_year is not None  # the payout side does not depend on power


def test_build_odds_missing_power_reports_unknown_cost_not_zero():
    out = build_odds(FleetSummary(hashrate_hs=1e12), NET, Settings())
    eco = out["economics"]
    assert eco["power_w"] is None
    for name in COST_FIELDS:
        assert eco[name] is None, name
    assert eco["power_complete"] is False
    assert eco["cost_note"]
    assert eco["expected_value_per_year"] is not None
    assert not any("Electricity costs about 0 " in line for line in out["plain_english"])


def test_build_odds_explicit_zero_power_override_costs_nothing():
    eco = build_odds(FleetSummary(hashrate_hs=1e12), NET, Settings(), power_w=0.0)["economics"]
    assert eco["power_w"] == 0.0
    assert eco["cost_per_day"] == 0.0
    assert eco["power_complete"] is True


def test_build_odds_power_override_fills_in_for_missing_telemetry():
    eco = build_odds(FleetSummary(hashrate_hs=1e12), NET, Settings(), power_w=100.0)["economics"]
    assert eco["cost_per_day"] == pytest.approx(_daily_cost(100.0))
    assert eco["cost_per_year"] == pytest.approx(_daily_cost(100.0) * 365.25)
    assert eco["power_complete"] is True


def test_build_odds_measured_power_is_complete():
    summary = build_summary([_runtime("a", 20.0), _runtime("b", 30.0)], Settings())
    assert summary.devices_without_power == 0
    eco = build_odds(summary, NET, Settings())["economics"]
    assert eco["power_w"] == pytest.approx(50.0)
    assert eco["cost_per_day"] == pytest.approx(_daily_cost(50.0))
    assert eco["power_complete"] is True
    assert eco["cost_note"] is None


def test_mixed_fleet_flags_incomplete_power_coverage():
    summary = build_summary([_runtime("a", 20.0), _runtime("b", None)], Settings())
    assert summary.devices_without_power == 1
    out = build_odds(summary, NET, Settings())
    eco = out["economics"]
    assert eco["power_complete"] is False
    assert eco["cost_note"]
    assert eco["cost_per_day"] == pytest.approx(_daily_cost(20.0))  # only the miner that reports power
    assert any(eco["cost_note"] in line for line in out["plain_english"])


def test_fleet_with_no_power_reporting_miner_has_unknown_cost():
    summary = build_summary([_runtime("a", None), _runtime("b", None)], Settings())
    assert summary.power_w is None and summary.devices_without_power == 2
    eco = build_odds(summary, NET, Settings())["economics"]
    assert eco["cost_per_day"] is None and eco["power_complete"] is False


async def test_odds_api_returns_null_cost_when_power_unknown(api):
    client, ctx, _ = api
    ctx.network.state = NET
    eco = (await client.get("/api/v1/odds")).json()["economics"]
    assert eco["power_w"] is None and eco["cost_per_day"] is None
    zero = (await client.get("/api/v1/odds", params={"power_w": 0})).json()["economics"]
    assert zero["cost_per_day"] == 0


async def test_odds_api_has_no_break_even_price(api):
    client, ctx, _ = api
    ctx.network.state = NET
    for params in ({}, {"power_w": 100}):
        eco = (await client.get("/api/v1/odds", params=params)).json()["economics"]
        assert "break_even_btc_price" not in eco
        assert "ev_to_cost_ratio" in eco
    assert "break_even_btc_price" not in build_odds(FleetSummary(hashrate_hs=1e12), NET, Settings(), power_w=100.0)["economics"]
