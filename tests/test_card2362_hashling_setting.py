"""Card #2362: the "Hashling pop-ups" switch is a server-owned UI setting, on by default.

It lives with the other look-and-feel settings (``ui.reduce_motion``, ``ui.sound_on_block``) so that the wall display, which
is another browser, follows the owner's choice. The server only stores it: Hashling itself is drawn by the web app.
"""

from typing import Any


async def _ui(c) -> dict[str, Any]:
    r = await c.get("/api/v1/settings")
    assert r.status_code == 200, r.text
    return r.json()["ui"]


async def _patch_ui(c, **fields: Any) -> dict[str, Any]:
    r = await c.patch("/api/v1/settings", json={"ui": fields})
    assert r.status_code == 200, r.text
    return r.json()["ui"]


async def test_hashling_popups_are_on_by_default(api):
    c, *_ = api
    assert (await _ui(c))["hashling_popups"] is True


async def test_switching_them_off_is_stored_and_returned(api):
    c, *_ = api
    saved = await _patch_ui(c, hashling_popups=False)
    assert saved["hashling_popups"] is False
    assert (await _ui(c))["hashling_popups"] is False

    saved = await _patch_ui(c, hashling_popups=True)
    assert saved["hashling_popups"] is True


async def test_changing_other_look_settings_leaves_the_switch_alone(api):
    c, *_ = api
    await _patch_ui(c, hashling_popups=False)
    ui = await _patch_ui(c, theme="light", reduce_motion=True)
    assert ui["hashling_popups"] is False
    assert ui["theme"] == "light"


async def test_the_switch_survives_a_reload_from_storage(api):
    c, ctx, _ = api
    await _patch_ui(c, hashling_popups=False)
    await ctx.settings.load()
    assert (await _ui(c))["hashling_popups"] is False


async def test_settings_saved_before_the_switch_existed_load_with_pop_ups_on(api):
    c, ctx, _ = api
    await ctx.store.kv_set("settings", {"ui": {"theme": "light", "reduce_motion": True}})
    await ctx.settings.load()
    ui = await _ui(c)
    assert ui["hashling_popups"] is True
    assert ui["theme"] == "light"
    assert ui["reduce_motion"] is True
