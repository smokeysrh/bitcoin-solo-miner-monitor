import json

import pytest

from bsmm.sim.axeos import AxeOSSim
from bsmm.sim.bitcoin_core import FakeBitcoinCore

EX_ADDR = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"


async def add_miner(c, ctx, hosts, host="gamma.test", seed=1, mac="AA:BB:CC:00:00:11", profile="gamma"):
    hosts[host] = AxeOSSim(profile, seed=seed, mac=mac).app()
    # keep the cgminer driver off the real network in tests
    res = await ctx.fleet.add_by_host(host, drivers=["axeos"])
    await ctx.fleet._poll_once(ctx.fleet.runtimes[res.device.id])
    return res.device


async def test_meta_is_public_and_has_no_secrets(api):
    c, ctx, _ = api
    r = await c.get("/api/v1/meta")
    assert r.status_code == 200
    j = r.json()
    assert j["app"] == "bitcoin-solo-miner-monitor" and j["api_version"] == "v1"
    assert j["auth"]["mode"] == "none" and j["links"]["openapi"].endswith("/openapi.json")
    assert j["setup"]["devices"] == 0 and j["setup"]["has_node_or_pool"] is False
    blob = json.dumps(j).lower()
    assert not any(bad in blob for bad in ("password_hash", "secret", "rpc_password", "bsmm_session"))


async def test_error_shape_is_consistent(api):
    c, *_ = api
    r = await c.get("/api/v1/devices/nope")
    assert r.status_code == 404
    e = r.json()["error"]
    assert e["code"] == "not_found" and e["status"] == 404 and "hint" in e and "nope" in e["message"]
    r = await c.get("/api/v1/does-not-exist")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
    r = await c.post("/api/v1/devices", json={"nothost": 1})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    assert r.json()["error"]["details"][0]["field"] == "host"
    r = await c.get("/api/v1/fleet/history", params={"range": "banana"})
    assert r.status_code == 400 and "30m" in r.json()["error"]["hint"]


async def test_device_lifecycle_over_the_api(api):
    c, ctx, hosts = api
    hosts["gamma.test"] = AxeOSSim("gamma", seed=1, mac="AA:BB:CC:00:00:11").app()
    # add by host (drivers=axeos is not exposed in the API; the cgminer probe against a fake host name fails fast offline)
    from bsmm.drivers import registry

    orig = registry.DRIVER_CLASSES.copy()
    registry.DRIVER_CLASSES.pop("cgminer")
    try:
        r = await c.post("/api/v1/devices", json={"host": "gamma.test", "name": "Garage", "tags": ["garage"]})
    finally:
        registry.DRIVER_CLASSES.update(orig)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["created"] is True and body["device"]["name"] == "Garage"
    dev_id = body["device"]["id"]
    await ctx.fleet._poll_once(ctx.fleet.runtimes[dev_id])

    j = (await c.get(f"/api/v1/devices/{dev_id}")).json()
    assert j["status"] == "online" and j["telemetry"]["hashrate_hs"] > 1e12 and j["family"] == "bitaxe"

    listed = (await c.get("/api/v1/devices", params={"status": "online", "tag": "garage", "q": "gamma"})).json()
    assert [d["id"] for d in listed] == [dev_id]
    assert (await c.get("/api/v1/devices", params={"status": "offline"})).json() == []

    patched = await c.patch(f"/api/v1/devices/{dev_id}", json={"name": "Garage Gamma", "notes": "top shelf"})
    assert patched.json()["name"] == "Garage Gamma" and patched.json()["notes"] == "top shelf"
    raw = (await c.get(f"/api/v1/devices/{dev_id}/raw")).json()
    assert raw["raw"]["ASICModel"] == "BM1370"
    fleet = (await c.get("/api/v1/fleet")).json()
    assert fleet["devices_total"] == 1 and fleet["hashrate_hs"] > 1e12

    assert (await c.delete(f"/api/v1/devices/{dev_id}")).json() == {"ok": True}
    assert (await c.get(f"/api/v1/devices/{dev_id}")).status_code == 404


async def test_adding_an_unknown_host_is_a_helpful_404(api):
    c, ctx, _ = api
    from bsmm.drivers import registry

    orig = registry.DRIVER_CLASSES.copy()
    registry.DRIVER_CLASSES.pop("cgminer")
    try:
        r = await c.post("/api/v1/devices", json={"host": "nowhere.test"})
    finally:
        registry.DRIVER_CLASSES.update(orig)
    assert r.status_code == 404 and r.json()["error"]["code"] == "no_miner_found"


async def test_actions_and_audit(api):
    c, ctx, hosts = api
    dev = await add_miner(c, ctx, hosts)
    r = await c.post(f"/api/v1/devices/{dev.id}/actions/identify", json={})
    assert r.status_code == 200 and r.json()["ok"] is True
    r = await c.post(f"/api/v1/devices/{dev.id}/actions/set_tuning", json={"params": {"frequency_mhz": 550}})
    assert r.status_code == 403 and r.json()["error"]["code"] == "not_allowed"
    r = await c.post(f"/api/v1/devices/{dev.id}/actions/launch_missiles", json={})
    assert r.status_code == 400 and "unknown action" in r.json()["error"]["message"]
    r = await c.post(f"/api/v1/devices/{dev.id}/actions/restart", json={"dry_run": True})
    assert r.json()["dry_run"] is True
    audit = (await c.get(f"/api/v1/devices/{dev.id}/audit")).json()["audit"]
    assert [a["action"] for a in audit][:1] == ["identify"]


async def test_bulk_actions_preview_by_default(api):
    c, ctx, hosts = api
    a = await add_miner(c, ctx, hosts, "a.test", 1, "AA:BB:CC:00:00:11")
    b = await add_miner(c, ctx, hosts, "b.test", 2, "AA:BB:CC:00:00:22")
    sim_a = ctx.fleet.runtimes[a.id].driver
    r = await c.post("/api/v1/devices/actions", json={"action": "restart", "all": True})
    j = r.json()
    assert j["dry_run"] is True and len(j["results"]) == 2 and all(x["dry_run"] for x in j["results"])
    assert sim_a is not None
    r = await c.post("/api/v1/devices/actions", json={"action": "identify", "device_ids": [a.id, "dev_missing"], "dry_run": False})
    res = r.json()["results"]
    assert res[0]["ok"] is True and res[1]["ok"] is False and "unknown miner" in res[1]["error"]
    assert (await c.post("/api/v1/devices/actions", json={"action": "restart"})).status_code == 400
    assert b.id  # both exist


async def test_history_and_overview(api):
    c, ctx, hosts = api
    dev = await add_miner(c, ctx, hosts)
    await ctx.fleet._poll_once(ctx.fleet.runtimes[dev.id])
    await ctx.fleet._flush_samples()
    h = (await c.get("/api/v1/fleet/history", params={"range": "1h", "metrics": "hashrate_hs,efficiency_j_th", "step": 10})).json()
    assert any(v for v in h["series"]["hashrate_hs"])
    dh = (await c.get(f"/api/v1/devices/{dev.id}/history", params={"range": "1h", "metrics": "temp_asic_c"})).json()
    assert "temp_asic_c" in dh["series"] and len(dh["t"]) == len(dh["series"]["temp_asic_c"])
    bad = await c.get("/api/v1/fleet/history", params={"metrics": "nonsense"})
    assert bad.status_code == 400 and "hashrate_hs" in bad.json()["error"]["hint"]
    o = (await c.get("/api/v1/overview")).json()
    assert o["summary"]["devices_total"] == 1 and o["odds"]["available"] is False  # no network data yet


async def test_odds_with_network_data_and_what_if(api):
    c, ctx, hosts = api
    await add_miner(c, ctx, hosts)
    # feed the network service a node snapshot (the real flow polls sources; here we inject directly)
    from bsmm.engine.network import NetworkState

    ctx.network.state = NetworkState(available=True, height=972_175, difficulty=140_577_680_051_919.6, network_hashrate_hs=1.03e21,
                                     block_reward_btc=3.2, btc_price=82_000.0)
    o = (await c.get("/api/v1/odds")).json()
    assert o["available"] and o["live"] is True
    assert 0 < o["horizons"]["year"]["probability"] < 1e-3
    assert o["economics"]["cost_per_day"] > 0 and o["economics"]["expected_value_per_year"] > 0
    assert any("fleet" in s.lower() or "hold about" in s for s in o["plain_english"])
    big = (await c.get("/api/v1/odds", params={"hashrate_ths": 1000})).json()
    assert big["live"] is False and big["horizons"]["year"]["probability"] > o["horizons"]["year"]["probability"] * 100
    assert (await c.get("/api/v1/odds", params={"hashrate_ths": -1})).status_code == 422


async def test_settings_validation_and_patch(api):
    c, ctx, _ = api
    s = (await c.get("/api/v1/settings")).json()
    assert s["energy"]["price_per_kwh"] == 0.12
    r = await c.patch("/api/v1/settings", json={"energy": {"price_per_kwh": 0.09}})
    assert r.status_code == 200 and r.json()["energy"]["price_per_kwh"] == 0.09
    assert (await c.get("/api/v1/settings")).json()["polling"]["interval_s"] == 10.0  # untouched siblings
    bad = await c.patch("/api/v1/settings", json={"energy": {"price_per_kwh": -1}})
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "validation_error"
    bad = await c.patch("/api/v1/settings", json={"mining": {"addresses": ["bc1qtotallywrong"]}})
    assert bad.status_code == 422 and "valid Bitcoin address" in bad.json()["error"]["message"]
    ok = await c.patch("/api/v1/settings", json={"mining": {"addresses": [EX_ADDR]}})
    assert ok.json()["mining"]["addresses"] == [EX_ADDR]
    # password mode cannot be switched on without a password
    r = await c.patch("/api/v1/settings", json={"auth": {"mode": "password"}})
    assert r.status_code == 400


async def test_auth_flow_and_token_scopes(api):
    c, ctx, hosts = api
    await add_miner(c, ctx, hosts)
    r = await c.post("/api/v1/auth/password", json={"new_password": "correct horse battery"})
    assert r.status_code == 200 and r.json()["auth_mode"] == "password"
    assert "bsmm_session" in r.headers.get("set-cookie", "")
    # the cookie from setting the password lets this client in; a fresh client is locked out
    import httpx

    from bsmm.api.app import create_app

    anon = httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(ctx=ctx)), base_url="http://bsmm.test")
    denied = await anon.get("/api/v1/devices")
    assert denied.status_code == 401 and denied.json()["error"]["code"] == "auth_required" and "Bearer" in denied.json()["error"]["hint"]
    assert (await anon.get("/api/v1/meta")).status_code == 200  # meta stays public
    assert (await anon.get("/api/v1/health")).status_code == 200
    bad = await anon.post("/api/v1/auth/login", json={"password": "wrong"})
    assert bad.status_code == 401 and bad.json()["error"]["code"] == "bad_password"
    good = await anon.post("/api/v1/auth/login", json={"password": "correct horse battery"})
    assert good.status_code == 200
    me = (await anon.get("/api/v1/auth/me")).json()
    assert me == {"name": "admin", "scope": "admin", "via": "session"}

    # tokens: created by the admin, scopes enforced, plaintext shown once
    tok = (await c.post("/api/v1/auth/tokens", json={"name": "agent", "scope": "read"})).json()
    assert tok["token"].startswith("bsmm_") and "cannot be shown again" in tok["warning"]
    listing = (await c.get("/api/v1/auth/tokens")).json()["tokens"]
    assert listing and "token" not in listing[0] and "hash" not in listing[0]
    bearer = httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(ctx=ctx)), base_url="http://bsmm.test",
                               headers={"Authorization": f"Bearer {tok['token']}"})
    assert (await bearer.get("/api/v1/devices")).status_code == 200
    forbidden = await bearer.post("/api/v1/devices/actions", json={"action": "restart", "all": True})
    assert forbidden.status_code == 403 and forbidden.json()["error"]["code"] == "insufficient_scope"
    assert (await bearer.patch("/api/v1/settings", json={"energy": {"price_per_kwh": 0.5}})).status_code == 403
    assert (await bearer.get("/api/v1/auth/tokens")).status_code == 403
    # revoke
    assert (await c.delete(f"/api/v1/auth/tokens/{tok['id']}")).json() == {"ok": True}
    assert (await bearer.get("/api/v1/devices")).status_code == 401
    for cl in (anon, bearer):
        await cl.aclose()


async def test_cookie_sessions_block_cross_site_writes(api):
    c, ctx, _ = api
    await c.post("/api/v1/auth/password", json={"new_password": "correct horse battery"})
    ok = await c.patch("/api/v1/settings", json={"energy": {"price_per_kwh": 0.2}}, headers={"Origin": "http://bsmm.test"})
    assert ok.status_code == 200
    evil = await c.patch("/api/v1/settings", json={"energy": {"price_per_kwh": 0.3}}, headers={"Origin": "http://evil.example"})
    assert evil.status_code == 403 and evil.json()["error"]["code"] == "cross_site_blocked"


async def test_public_read_mode_allows_get_but_not_writes(api):
    import httpx

    from bsmm.api.app import create_app

    c, ctx, hosts = api
    await add_miner(c, ctx, hosts)
    await c.post("/api/v1/auth/password", json={"new_password": "correct horse battery"})
    await c.patch("/api/v1/settings", json={"auth": {"public_read": True}})
    anon = httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(ctx=ctx)), base_url="http://bsmm.test")
    assert (await anon.get("/api/v1/overview")).status_code == 200
    assert (await anon.post("/api/v1/devices/actions", json={"action": "restart", "all": True})).status_code == 401
    assert (await anon.get("/api/v1/auth/tokens")).status_code == 403  # read scope only
    await anon.aclose()


async def test_sources_wizard_flow_with_a_fake_node(api):
    c, ctx, _ = api
    node = FakeBitcoinCore()
    import httpx

    from tests.conftest import MultiHostTransport

    ctx.http._transport = MultiHostTransport({"node.test": node.app()})  # type: ignore[attr-defined]
    kinds = (await c.get("/api/v1/sources/kinds")).json()["kinds"]
    assert {k["kind"] for k in kinds} == {"bitcoin_core", "public_pool", "ckpool", "mempool_space"}
    bad = await c.post("/api/v1/sources/test", json={"kind": "bitcoin_core", "url": "http://node.test:8332", "secret": {"rpc_user": "umbrel", "rpc_password": "nope"}})
    assert bad.json()["ok"] is False and any("Umbrel" in h for h in bad.json()["hints"])
    refused = await c.post("/api/v1/sources", json={"kind": "bitcoin_core", "url": "http://node.test:8332", "secret": {"rpc_user": "umbrel", "rpc_password": "nope"}})
    assert refused.status_code == 422 and refused.json()["error"]["code"] == "connection_failed"
    good = await c.post("/api/v1/sources", json={"kind": "bitcoin_core", "name": "My node", "url": "http://node.test:8332",
                                                   "secret": {"rpc_user": "umbrel", "rpc_password": "secret"}})
    assert good.status_code == 200, good.text
    src = good.json()["source"]
    assert src["has_secret"] is True and "secret" not in src and "secret_enc" not in src
    assert "secret" not in json.dumps((await c.get("/api/v1/sources")).json()).replace("has_secret", "")
    assert (await c.delete(f"/api/v1/sources/{src['id']}")).json() == {"ok": True}
    assert (await c.post("/api/v1/sources", json={"kind": "evil", "url": "x"})).status_code == 400
    del httpx


async def test_channels_never_leak_secrets(api):
    c, *_ = api
    types = (await c.get("/api/v1/notifications/channel-types")).json()["channel_types"]
    assert {t["kind"] for t in types} >= {"discord", "telegram", "ntfy", "email", "webhook"}
    tele = next(t for t in types if t["kind"] == "telegram")
    assert any(f["name"] == "bot_token" and f["secret"] for f in tele["fields"])
    r = await c.post("/api/v1/notifications/channels", json={"kind": "telegram", "name": "Phone", "config": {"chat_id": "42", "bot_token": "123:SECRET"}})
    assert r.status_code == 200
    ch = r.json()["channel"]
    assert ch["has_secret"] is True and "SECRET" not in json.dumps(ch)
    assert "SECRET" not in (await c.get("/api/v1/notifications/channels")).text
    stored = await __import__("asyncio").sleep(0)  # noqa: F841
    assert (await c.post("/api/v1/notifications/channels", json={"kind": "carrier-pigeon", "name": "x"})).status_code == 400
    assert (await c.delete(f"/api/v1/notifications/channels/{ch['id']}")).json() == {"ok": True}


async def test_alert_rules_api(api):
    c, *_ = api
    # the app was not started, so default rules are created on demand by the engine; do it explicitly
    await (await _ctx(c)).alerts.ensure_default_rules()
    rules = (await c.get("/api/v1/alerts/rules")).json()["rules"]
    kinds = {r["kind"] for r in rules}
    assert {"device_offline", "temp_high", "block_found", "new_best_share"} <= kinds
    types = (await c.get("/api/v1/alerts/rule-types")).json()["rule_types"]
    assert next(t for t in types if t["kind"] == "temp_high")["params"][0]["unit"] == "°C"
    created = await c.post("/api/v1/alerts/rules", json={"kind": "temp_high", "name": "Cooler limit", "params": {"asic_c": 65}})
    assert created.status_code == 200 and created.json()["rule"]["params"]["asic_c"] == 65
    rid = created.json()["rule"]["id"]
    bad = await c.patch(f"/api/v1/alerts/rules/{rid}", json={"params": {"asic_c": 999}})
    assert bad.status_code == 400 and "between" in bad.json()["error"]["message"]
    assert (await c.delete(f"/api/v1/alerts/rules/{rid}")).json() == {"ok": True}
    builtin = next(r for r in rules if r["builtin"])
    assert (await c.delete(f"/api/v1/alerts/rules/{builtin['id']}")).status_code == 400
    off = await c.patch(f"/api/v1/alerts/rules/{builtin['id']}", json={"enabled": False})
    assert off.json()["rule"]["enabled"] is False


async def _ctx(c):
    return c._transport.app.state.ctx  # type: ignore[attr-defined]


async def test_events_endpoint_paging(api):
    c, ctx, hosts = api
    for i in range(5):
        await ctx.events.emit("test_event", f"event {i}")
    page = (await c.get("/api/v1/events", params={"limit": 2, "type": "test_event"})).json()
    assert len(page["events"]) == 2 and page["next_before_id"]
    older = (await c.get("/api/v1/events", params={"limit": 10, "type": "test_event", "before_id": page["next_before_id"]})).json()
    assert len(older["events"]) == 3 and older["next_before_id"] is None


async def test_prometheus_metrics(api):
    c, ctx, hosts = api
    dev = await add_miner(c, ctx, hosts)
    text = (await c.get("/metrics")).text
    assert "# TYPE bsmm_fleet_hashrate_hashes_per_second gauge" in text
    assert f'bsmm_device_up{{device="{dev.id}"' in text
    assert "bsmm_device_hashrate_hashes_per_second{" in text
    assert text.endswith("\n")
    # every non-comment line is "name{labels} number"
    for line in text.splitlines():
        if line and not line.startswith("#"):
            assert len(line.rsplit(" ", 1)) == 2
            float(line.rsplit(" ", 1)[1])


async def test_agent_docs(api):
    c, *_ = api
    txt = await c.get("/llms.txt")
    assert txt.status_code == 200 and txt.text.startswith("# Bitcoin Solo Miner Monitor")
    assert "/api/v1/meta" in txt.text and "http://bsmm.test" in txt.text
    guide = (await c.get("/api/v1/agent/guide")).json()
    assert guide["api_base"] == "http://bsmm.test/api/v1" and len(guide["setup_recipe"]) >= 8
    assert any("dry_run" in s for s in guide["safety"])
    spec = (await c.get("/openapi.json")).json()
    assert spec["info"]["title"].startswith("Bitcoin Solo Miner Monitor")
    # every operation has an id, a summary and a tag: that is what makes the spec usable by agents
    for path, item in spec["paths"].items():
        for method, op in item.items():
            if method in {"get", "post", "patch", "delete", "put"}:
                assert op.get("operationId") and op.get("summary"), f"{method.upper()} {path}"


async def test_stream_rejects_unknown_topics(api):
    c, *_ = api
    # (the streaming behaviour itself is exercised against a real server in test_live_server.py)
    assert (await c.get("/api/v1/stream", params={"topics": "bogus"})).status_code == 400


async def test_export_import_roundtrip_without_secrets(api):
    c, ctx, hosts = api
    await add_miner(c, ctx, hosts)
    await c.post("/api/v1/notifications/channels", json={"kind": "ntfy", "name": "Phone", "config": {"topic": "t"}, "secret": {"token": "tk_secret"}})
    exp = (await c.get("/api/v1/system/export")).json()
    assert exp["format"] == "bsmm-config-v1" and len(exp["devices"]) == 1
    assert "tk_secret" not in json.dumps(exp)
    again = (await c.post("/api/v1/system/import", json=exp)).json()
    assert again["added"]["devices"] == 0  # already there (matched by identity)
    exp["devices"][0]["host"] = "other.test"
    exp["devices"][0]["id"] = "dev_copy"
    exp["devices"][0]["mac"] = "AA:BB:CC:99:99:99"
    imp = (await c.post("/api/v1/system/import", json=exp)).json()
    assert imp["added"]["devices"] == 1
    assert (await c.post("/api/v1/system/import", json={"format": "nope"})).status_code == 400


async def test_diagnostics_and_update_endpoints(api):
    c, ctx, hosts = api
    d = (await c.get("/api/v1/system/diagnostics")).json()
    ids = {x["id"] for x in d["checks"]}
    assert {"database", "disk", "miners", "network-data", "notifications", "auth"} <= ids
    assert all(x["status"] in {"pass", "warn", "fail"} for x in d["checks"])
    up = (await c.get("/api/v1/system/update")).json()
    assert up["disabled"] is True  # tests run offline
    assert (await c.get("/api/v1/system/info")).json()["schema_version"] >= 1


async def test_insights_for_an_empty_and_a_populated_install(api):
    c, ctx, hosts = api
    first = (await c.get("/api/v1/insights")).json()["insights"]
    assert [i["id"] for i in first] == ["no-miners"]
    await add_miner(c, ctx, hosts)
    ids = {i["id"] for i in (await c.get("/api/v1/insights")).json()["insights"]}
    assert {"no-node", "no-channel", "no-network"} <= ids
    assert (await c.post("/api/v1/insights/no-node/dismiss")).json() == {"ok": True}
    ids = {i["id"] for i in (await c.get("/api/v1/insights")).json()["insights"]}
    assert "no-node" not in ids


async def test_body_size_limit(api):
    c, *_ = api
    r = await c.post("/api/v1/system/import", content=b"x" * 10, headers={"content-length": str(10 * 1024 * 1024), "content-type": "application/json"})
    assert r.status_code == 413 and r.json()["error"]["code"] == "too_large"


async def test_security_headers(api):
    c, *_ = api
    r = await c.get("/api/v1/health")
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
    assert r.headers["cache-control"] == "no-store" and r.headers["x-request-id"]
    assert pytest is not None
