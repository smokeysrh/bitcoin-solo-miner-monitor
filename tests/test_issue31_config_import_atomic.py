"""Issue #31: a config import is all-or-nothing, and a rejected import changes nothing."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from bsmm.api.app import create_app


@pytest.fixture
async def imp(lan):
    """(client, ctx). Server errors come back as HTTP 500 instead of raising into the test."""
    ctx, _ = lan
    app = create_app(ctx=ctx)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://bsmm.test") as c:
        yield c, ctx


def _device(dev_id: str, host: str, mac: str) -> dict[str, Any]:
    return {"id": dev_id, "name": dev_id, "driver": "axeos", "family": "axeos", "model": "Gamma",
            "host": host, "port": 80, "mac": mac}


def _file(**parts: Any) -> dict[str, Any]:
    return {"format": "bsmm-config-v1", **parts}


GOOD_SETTINGS = {"general": {"instance_name": "Imported name"}}
GOOD_DEVICE = _device("dev_first", "first.test", "AA:BB:CC:00:00:01")
GOOD_CHANNEL = {"id": "ch_first", "kind": "ntfy", "name": "Phone", "config": {"topic": "t"}}
GOOD_SOURCE = {"id": "src_first", "kind": "mempool_space", "name": "Public"}


async def _snapshot(ctx) -> dict[str, Any]:
    return {
        "settings_kv": await ctx.store.kv_get("settings"),
        "settings": ctx.settings.current.model_dump(),
        "devices": [d.id for d in await ctx.store.list_devices()],
        "runtimes": sorted(ctx.fleet.runtimes),
        "rules": [r.model_dump() for r in await ctx.store.list_rules()],
        "channels": [c.id for c in await ctx.store.list_channels()],
        "sources": [s.id for s in await ctx.store.list_sources()],
    }


BAD_LATE_PARTS = {
    "rule_out_of_range": {"rules": [{"id": "rule_bad", "name": "bad", "kind": "temp_high", "params": {"asic_c": 5000}}]},
    "rule_unknown_kind": {"rules": [{"id": "rule_bad", "name": "bad", "kind": "no_such_rule"}]},
    "rule_negative_cooldown": {"rules": [{"id": "rule_bad", "name": "bad", "kind": "temp_high", "cooldown_s": -5}]},
    "rule_malformed": {"rules": [{"id": "rule_bad"}]},
    "source_malformed": {"sources": [{"id": "src_bad"}]},
    "source_unknown_kind": {"sources": [{"id": "src_bad", "kind": "no_such_source", "name": "bad"}]},
    "device_malformed": {"devices": [GOOD_DEVICE, {"id": "dev_bad", "name": "bad"}]},
    "device_duplicate_id": {"devices": [GOOD_DEVICE, _device("dev_first", "second.test", "AA:BB:CC:00:00:02")]},
    "settings_invalid_value": {"settings": {"general": {"instance_name": "x" * 500}}},
}


@pytest.mark.parametrize("name", list(BAD_LATE_PARTS))
async def test_rejected_import_changes_nothing(imp, name):
    c, ctx = imp
    before = await _snapshot(ctx)
    payload = _file(settings=GOOD_SETTINGS, channels=[GOOD_CHANNEL], sources=[GOOD_SOURCE], devices=[GOOD_DEVICE],
                    **BAD_LATE_PARTS[name])
    r = await c.post("/api/v1/system/import", json=payload)
    assert r.status_code in (400, 422), r.text
    assert await _snapshot(ctx) == before


async def test_failed_write_rolls_back_every_earlier_write(imp, monkeypatch):
    c, ctx = imp
    before = await _snapshot(ctx)

    async def fail(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("injected write failure")

    monkeypatch.setattr(ctx.store, "save_source", fail)
    payload = _file(settings=GOOD_SETTINGS, devices=[GOOD_DEVICE], channels=[GOOD_CHANNEL], sources=[GOOD_SOURCE])
    r = await c.post("/api/v1/system/import", json=payload)
    assert r.status_code == 500
    assert await _snapshot(ctx) == before


async def test_valid_import_applies_everything_once(imp):
    c, ctx = imp
    rule = {"id": "rule_extra", "name": "Hot", "kind": "temp_high", "params": {"asic_c": 80}}
    payload = _file(settings=GOOD_SETTINGS, devices=[GOOD_DEVICE], rules=[rule], channels=[GOOD_CHANNEL],
                    sources=[GOOD_SOURCE])
    r = await c.post("/api/v1/system/import", json=payload)
    assert r.status_code == 200, r.text
    assert r.json()["added"] == {"devices": 1, "rules": 1, "channels": 1, "sources": 1}
    assert ctx.settings.current.general.instance_name == "Imported name"
    assert (await ctx.store.kv_get("settings"))["general"]["instance_name"] == "Imported name"
    assert sorted(ctx.fleet.runtimes) == ["dev_first"]
    assert (await ctx.store.get_rule("rule_extra")).params["asic_c"] == 80.0
    assert not (await ctx.store.get_channel("ch_first")).enabled
    assert not (await ctx.store.get_source("src_first")).enabled
    again = await c.post("/api/v1/system/import", json=payload)
    assert again.json()["added"] == {"devices": 0, "rules": 0, "channels": 0, "sources": 0}
