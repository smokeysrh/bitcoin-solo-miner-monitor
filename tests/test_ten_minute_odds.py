"""Fixed-window odds, not a prediction of the next network block's timestamp."""
import json
import math

import pytest

from bsmm import mining
from bsmm.engine.network import NetworkState
from bsmm.engine.odds import build_odds
from bsmm.models import FleetSummary
from bsmm.settings import Settings


@pytest.mark.parametrize(("hashrate", "difficulty"), [(0, 1e14), (1e12, 1e14), (1e-100, 1e100), (1e100, 1e-100), (1e308, 1e308)])
def test_ten_minutes_fixed_window_and_monotonicity(hashrate, difficulty):
    report = mining.odds_report(hashrate, difficulty).as_dict()
    horizons = report["horizons"]
    assert horizons["ten_minutes"]["seconds"] == 600
    p = horizons["ten_minutes"]["probability"]
    expected = -math.expm1(-((hashrate / difficulty) / mining.HASHES_PER_DIFF1) * 600)
    assert math.isfinite(p) and p == pytest.approx(expected)
    probabilities = [v["probability"] for v in horizons.values()]
    assert probabilities == sorted(probabilities)
    assert all(0 <= p <= 1 for p in probabilities)


async def test_ten_minutes_live_whatif_and_missing_api(api):
    client, ctx, _ = api
    assert (await client.get("/api/v1/odds")).json()["available"] is False
    ctx.network.state = NetworkState(difficulty=1e14)
    live = (await client.get("/api/v1/odds")).json()
    assert live["horizons"]["ten_minutes"]["probability"] == 0
    for rate in (0, 1, 1e10):
        result = await client.get("/api/v1/odds", params={"hashrate_ths": rate})
        assert result.status_code == 200
        odds = result.json()
        h = odds["horizons"]["ten_minutes"]
        assert h["seconds"] == 600
        assert h["probability"] == pytest.approx(mining.probability_within(rate*1e12, 1e14, 600))
        assert h["probability"] <= odds["horizons"]["hour"]["probability"]


def test_ten_minutes_does_not_shift_annual_plain_english():
    out = build_odds(FleetSummary(hashrate_hs=1e12), NetworkState(difficulty=1e14), Settings())
    from bsmm.units import format_odds
    assert format_odds(out["horizons"]["year"]["probability"]) in out["plain_english"][1]
    assert any("exact future block time is unknown" in line for line in out["plain_english"])


@pytest.mark.parametrize("parameter", ["hashrate_ths", "difficulty", "power_w", "growth"])
@pytest.mark.parametrize("bad", ["nan", "inf", "-inf"])
async def test_odds_nonfinite_query_rejected(api, parameter, bad):
    client, _, _ = api
    assert (await client.get("/api/v1/odds", params={parameter: bad})).status_code == 422


async def test_ten_minutes_overview_cli_mcp_agree(lan):
    from mcp.client import Client

    from bsmm.api.app import create_app

    from .live import serve
    from .test_cli import cli, jout

    ctx, _ = lan
    ctx.network.state = NetworkState(difficulty=1e14)
    async with serve(create_app(ctx=ctx)) as base:
        human = await cli("odds", "--url", base, "--hashrate-ths", "1")
        assert human.exit_code == 0
        assert "Next 10 minutes" in human.stdout
        machine = jout(await cli("odds", "--url", base, "--json", "--hashrate-ths", "1"))
        assert machine["horizons"]["ten_minutes"]["seconds"] == 600
        async with Client(f"{base}/mcp") as mcp:
            result = await mcp.call_tool("get_odds", {"hashrate_ths": 1})
            assert not result.is_error
            # The actual MCP tool serializes the same REST response.
            text = json.dumps(result.model_dump(mode="json"))
            assert "ten_minutes" in text and "600" in text
        import httpx
        async with httpx.AsyncClient() as http:
            overview = (await http.get(f"{base}/api/v1/overview")).json()
            assert overview["odds"]["horizons"]["ten_minutes"]["seconds"] == 600


@pytest.mark.parametrize("growth", [-0.9, 0, 0.3, 10])
def test_ten_minutes_growth_is_monotone(growth):
    horizons = mining.odds_report(1e12, 1e14, difficulty_growth_per_year=growth).horizons
    p = [h.probability for h in horizons]
    assert p == sorted(p)
    assert horizons[0].name == "ten_minutes" and horizons[0].seconds == 600
