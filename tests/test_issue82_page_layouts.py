"""Issue #82: the Bitcoin and Odds & costs page layouts are saved per page in the existing settings.

The server keeps each layout as an opaque dictionary (like ``ui.dashboard``), so these tests use arbitrary layout
content and check only what the server owns: that each page's value is stored, returned, replaced whole, reset on
its own, kept across a reload, and absent (null) in settings saved before the feature existed.
"""

from typing import Any

BITCOIN = {"version": 1, "cards": ["node", "blocks"]}
ODDS = {"version": 1, "cards": ["plain", "hero"]}
DASHBOARD = {"version": 1, "widgets": [{"id": "hero", "span": 8}]}


async def _ui(c) -> dict[str, Any]:
    r = await c.get("/api/v1/settings")
    assert r.status_code == 200, r.text
    return r.json()["ui"]


async def _patch_ui(c, **fields: Any) -> dict[str, Any]:
    r = await c.patch("/api/v1/settings", json={"ui": fields})
    assert r.status_code == 200, r.text
    return r.json()["ui"]


async def test_each_page_layout_is_stored_and_returned(api):
    c, *_ = api
    assert (await _ui(c)).get("bitcoin_page") is None
    assert (await _ui(c)).get("odds_page") is None

    saved = await _patch_ui(c, bitcoin_page=BITCOIN)
    assert saved["bitcoin_page"] == BITCOIN
    ui = await _ui(c)
    assert ui["bitcoin_page"] == BITCOIN
    assert ui["odds_page"] is None

    saved = await _patch_ui(c, odds_page=ODDS)
    assert saved["odds_page"] == ODDS
    ui = await _ui(c)
    assert ui["odds_page"] == ODDS
    assert ui["bitcoin_page"] == BITCOIN


async def test_resetting_one_page_leaves_the_other_pages_alone(api):
    c, *_ = api
    await _patch_ui(c, dashboard=DASHBOARD, bitcoin_page=BITCOIN, odds_page=ODDS)

    ui = await _patch_ui(c, bitcoin_page=None)
    assert ui["bitcoin_page"] is None
    assert ui["odds_page"] == ODDS
    assert ui["dashboard"] == DASHBOARD

    ui = await _patch_ui(c, odds_page=None)
    assert ui["odds_page"] is None
    assert ui["dashboard"] == DASHBOARD


async def test_a_new_page_layout_replaces_the_old_one_whole(api):
    c, *_ = api
    await _patch_ui(c, bitcoin_page={**BITCOIN, "legacy": True})
    newer = {"version": 1, "cards": ["blocks", "node", "pool"]}  # no "legacy" key: it must not be merged in
    ui = await _patch_ui(c, bitcoin_page=newer)
    assert ui["bitcoin_page"] == newer
    assert (await _ui(c))["bitcoin_page"] == newer


async def test_page_layouts_survive_a_reload_from_storage(api):
    c, ctx, _ = api
    await _patch_ui(c, bitcoin_page=BITCOIN, odds_page=ODDS)
    await ctx.settings.load()
    ui = await _ui(c)
    assert ui["bitcoin_page"] == BITCOIN
    assert ui["odds_page"] == ODDS


async def test_settings_saved_before_page_layouts_existed_load_with_no_layouts(api):
    c, ctx, _ = api
    await ctx.store.kv_set("settings", {"ui": {"theme": "light", "dashboard": DASHBOARD}})
    await ctx.settings.load()
    ui = await _ui(c)
    assert ui["theme"] == "light"
    assert ui["dashboard"] == DASHBOARD
    assert ui["bitcoin_page"] is None
    assert ui["odds_page"] is None
