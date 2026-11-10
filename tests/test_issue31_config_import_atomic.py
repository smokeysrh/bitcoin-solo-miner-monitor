"""Issue #31: a config import is all-or-nothing, and a rejected import changes nothing."""

from __future__ import annotations

import asyncio
import copy
from typing import Any

import httpx
import pytest

from bsmm.api.app import create_app
from bsmm.settings import SettingsService


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
    good_parts: dict[str, Any] = {"settings": GOOD_SETTINGS, "channels": [GOOD_CHANNEL],
                                  "sources": [GOOD_SOURCE], "devices": [GOOD_DEVICE]}
    payload = _file(**{**good_parts, **BAD_LATE_PARTS[name]})  # the bad part replaces its good counterpart
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


@pytest.mark.parametrize("refresh_fails", [False, True], ids=["completes", "refresh_fails_after_commit"])
async def test_import_does_not_revert_a_concurrent_settings_update(imp, monkeypatch, refresh_fails):
    """An ordinary settings update is held mid-write while an import of a different field starts.

    Every settings document written to disk must keep the update's field, and a fresh load must show both.
    """
    c, ctx = imp
    real_kv_set = ctx.store.kv_set
    written: list[dict[str, Any]] = []
    held, release = asyncio.Event(), asyncio.Event()

    async def spy(key: str, value: Any) -> None:
        await real_kv_set(key, value)
        if key != "settings":
            return
        written.append(copy.deepcopy(value))
        if len(written) == 1:  # the ordinary update has written, but has not finished
            held.set()
            await release.wait()

    def fail_adopt(_dev: Any) -> None:
        raise RuntimeError("injected refresh failure")

    monkeypatch.setattr(ctx.store, "kv_set", spy)
    if refresh_fails:
        monkeypatch.setattr(ctx.fleet, "adopt", fail_adopt)
    ordinary = asyncio.create_task(ctx.settings.update({"ui": {"theme": "light"}}))
    try:
        await asyncio.wait_for(held.wait(), 5)
        importing = asyncio.create_task(c.post("/api/v1/system/import", json=_file(
            settings={"general": {"instance_name": "Imported while busy"}}, devices=[GOOD_DEVICE])))
        await asyncio.sleep(0.2)  # let the import reach its own settings write, or wait for the settings lock
    finally:
        release.set()
    _, response = await asyncio.wait_for(asyncio.gather(ordinary, importing), 10)

    assert response.status_code == (500 if refresh_fails else 200), response.text
    assert [doc["ui"]["theme"] for doc in written] == ["light"] * len(written), written
    loaded = await SettingsService(ctx.store).load()
    assert loaded.ui.theme == "light"
    assert loaded.general.instance_name == "Imported while busy"
