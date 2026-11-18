"""Card #2471: limit chart history request size (explicit windows and explicit steps)."""

import pytest

from bsmm.models import Device
from bsmm.storage.store import Store

FIVE_YEARS_S = 5 * 365 * 86400
BUCKET_CEILING = 5000
BUCKET_SLACK = 2  # the first bucket is aligned down and the last one is inclusive
RAW_SPAN_S = 2 * 3600  # the longest window still served from raw samples (1 s native buckets)
ONE_DAY_S = 86400


@pytest.fixture
async def store():
    s = await Store.open_memory()
    yield s
    await s.close()


async def add_device(ctx) -> Device:
    device = Device(id="size-device", name="Synthetic", driver="sim", family="sim", model="sim", host="127.0.0.1", port=1)
    await ctx.store.save_device(device)
    ctx.fleet._spawn(device)
    return device


def history_urls(device: Device) -> list[str]:
    return ["/api/v1/fleet/history", f"/api/v1/devices/{device.id}/history"]


async def test_small_explicit_step_is_raised_to_bound_the_bucket_count(store):
    h = await store.samples.history(metrics=["hashrate_hs"], start=0, end=RAW_SPAN_S, step=1)
    assert len(h.t) <= BUCKET_CEILING + BUCKET_SLACK
    assert h.step > 1  # the response reports the step actually used
    assert len(h.series["hashrate_hs"]) == len(h.t)


async def test_normal_windows_keep_their_step(store):
    explicit = await store.samples.history(metrics=["hashrate_hs"], start=0, end=3600, step=60)
    assert explicit.step == 60 and len(explicit.t) == 61
    automatic = await store.samples.history(metrics=["hashrate_hs"], start=0, end=ONE_DAY_S)
    assert automatic.step == 180  # span / 400, rounded down to a whole number of 1m buckets
    assert len(automatic.t) <= BUCKET_CEILING + BUCKET_SLACK


@pytest.mark.parametrize("route", [0, 1])
async def test_explicit_window_beyond_five_years_is_refused(api, route):
    c, ctx, _ = api
    device = await add_device(ctx)
    r = await c.get(history_urls(device)[route], params={"metrics": "hashrate_hs", "start": 0, "end": 10**12})
    assert r.status_code == 400, r.text
    assert r.json()["error"]["code"] == "bad_request"


@pytest.mark.parametrize("route", [0, 1])
async def test_explicit_window_of_five_years_still_works(api, route):
    c, ctx, _ = api
    device = await add_device(ctx)
    start = 1_000_000
    r = await c.get(history_urls(device)[route], params={"metrics": "hashrate_hs", "start": start, "end": start + FIVE_YEARS_S})
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["t"]) <= BUCKET_CEILING + BUCKET_SLACK


@pytest.mark.parametrize("route", [0, 1])
async def test_api_bounds_buckets_for_a_small_explicit_step(api, route):
    c, ctx, _ = api
    device = await add_device(ctx)
    r = await c.get(history_urls(device)[route], params={"metrics": "hashrate_hs", "range": "2h", "step": 1})
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["t"]) <= BUCKET_CEILING + BUCKET_SLACK
    assert body["step"] > 1


@pytest.mark.parametrize("route", [0, 1])
async def test_api_normal_range_is_unchanged(api, route):
    c, ctx, _ = api
    device = await add_device(ctx)
    r = await c.get(history_urls(device)[route], params={"metrics": "hashrate_hs", "range": "24h", "step": 60})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["step"] == 60
    assert len(body["t"]) <= ONE_DAY_S // 60 + BUCKET_SLACK
