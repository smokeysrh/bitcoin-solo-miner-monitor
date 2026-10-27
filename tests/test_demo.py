"""Demo mode must start, seed believable history, and serve it through the real API.

Regression: seeding crashed with ``You did not supply a value for binding parameter :hashrate_hs``
because offline (outage) buckets carry fewer columns than online ones.
"""

from __future__ import annotations

import time

import httpx
import pytest

from bsmm.api.app import create_app
from bsmm.config import RuntimeConfig
from bsmm.context import AppContext
from bsmm.demo import DEMO_FLEET, seed_demo
from bsmm.storage import metrics as mx


@pytest.fixture
async def demo_ctx(tmp_path):
    ctx = await AppContext.create(RuntimeConfig(data_dir=tmp_path, demo=True, offline=True))
    await seed_demo(ctx)
    yield ctx
    await ctx.fleet.stop()
    await ctx.http.aclose()
    await ctx.store.close()


async def test_seed_demo_creates_the_whole_fleet(demo_ctx):
    devices = await demo_ctx.store.list_devices()
    assert {d.name for d in devices} == {s["name"] for s in DEMO_FLEET}
    assert demo_ctx.settings.current.general.onboarding_done is True


async def test_demo_history_has_data_and_a_visible_outage(demo_ctx):
    now = time.time()
    gt = next(d for d in await demo_ctx.store.list_devices() if d.name == "Rack GT")
    hist = await demo_ctx.store.samples.history(metrics=["hashrate_hs", "online"], start=now - 24 * 3600, end=now, step=60, device_ids=[gt.id], per_device=True)
    series = hist.devices[gt.id]
    assert any(v for v in series["hashrate_hs"] if v), "online buckets carry a hashrate"
    assert any(v == 0 for v in series["online"]), "the 14 minute outage is recorded"
    dark = [h for h, o in zip(series["hashrate_hs"], series["online"], strict=True) if o == 0]
    assert dark and all(h is None for h in dark), "an offline bucket has no hashrate, not a fake zero"


async def test_demo_history_is_served_by_the_api(demo_ctx):
    app = create_app(ctx=demo_ctx)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://bsmm.test") as c:
        r = await c.get("/api/v1/fleet/history", params={"range": "24h", "metrics": "hashrate_hs,power_w"})
        assert r.status_code == 200
        body = r.json()
        assert len(body["t"]) > 10
        assert any(v for v in body["series"]["hashrate_hs"] if v)


async def test_insert_rollup_rows_tolerates_missing_metric_columns(demo_ctx):
    dev = (await demo_ctx.store.list_devices())[0]
    sparse = [{"device_id": dev.id, "bucket": 1_000_000, "n": 6, "online": 0.0}]
    await demo_ctx.store.samples.insert_rollup_rows("samples_1h", sparse)  # no exception
    row = await demo_ctx.store.db.fetchone("SELECT hashrate_hs, online FROM samples_1h WHERE device_id=? AND bucket=?", (dev.id, 1_000_000))
    assert row["hashrate_hs"] is None and row["online"] == 0.0


async def test_insert_rollup_rows_rejects_unknown_columns(demo_ctx):
    dev = (await demo_ctx.store.list_devices())[0]
    bad = [{"device_id": dev.id, "bucket": 1, "n": 1, "evil); DROP TABLE samples;--": 1}]
    with pytest.raises(ValueError, match="unknown rollup column"):
        await demo_ctx.store.samples.insert_rollup_rows("samples_1h", bad)


async def test_demo_miners_look_lived_in_not_freshly_booted(demo_ctx):
    """A first view must not show '3 accepted, 2 rejected = 40% reject rate'."""
    from bsmm.drivers.sim import _AXEOS, _CGMINER

    assert _AXEOS and _CGMINER
    for sim in _AXEOS.values():
        assert sim.shares_accepted > 500  # the Supra "rebooted 6 h ago", so it has the fewest (~850)
        assert sim.shares_rejected / sim.shares_accepted < 0.02
        assert time.time() - sim.started > 3600
    for csim in _CGMINER.values():
        assert csim.accepted > 500
        assert csim.rejected / csim.accepted < 0.02


def test_every_metric_has_a_rollup_column():
    # guards the column list insert_rollup_rows derives from the metric registry
    cols = {c for m in mx.METRICS for c in mx.rollup_columns(m)}
    assert "hashrate_hs" in cols and "hashrate_hs_max" in cols
