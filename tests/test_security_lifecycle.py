"""Offline regressions for the v1.1.1 security lifecycle findings."""
import asyncio
import json

import httpx
import pytest
from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials

from bsmm.api.app import MAX_BODY, create_app
from bsmm.api.deps import require
from bsmm.api.routes_fleet import stream
from bsmm.bitcoin_address import is_valid_address
from bsmm.capture import redact
from bsmm.config import RuntimeConfig
from bsmm.context import AppContext
from bsmm.models import Source
from bsmm.notify.channels import CHANNEL_CLASSES
from bsmm.sim.cgminer import CgminerSim
from bsmm.storage.store import Store
from tests.conftest import MultiHostTransport


@pytest.fixture
async def rig(tmp_path):
    hosts = {}
    http = httpx.AsyncClient(transport=MultiHostTransport(hosts), trust_env=False)
    store = await Store.open_memory()
    ctx = await AppContext.create(
        RuntimeConfig(data_dir=tmp_path, offline=True, no_update_check=True,
                      auth_mode=None, admin_password=None), store=store, http=http,
    )
    app = create_app(ctx=ctx)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
                                base_url="http://127.0.0.1:21841", trust_env=False) as client:
        try:
            yield client, ctx, hosts, app
        finally:
            if not ctx.http.is_closed:
                await ctx.stop()


async def protect(ctx):
    await ctx.auth.set_password("synthetic-test-password")
    await ctx.settings.update({"auth": {"mode": "password"}})


async def test_sec01_invalid_persistence_keeps_auth(rig):
    c, ctx, _, _ = rig
    await protect(ctx)
    assert (await c.get("/api/v1/auth/me")).status_code == 401
    raw = ctx.settings.current.model_dump()
    raw["ui"]["accent"] = "invalid-legacy-value"
    await ctx.store.kv_set("settings", raw)
    await ctx.settings.load()
    assert (await c.get("/api/v1/auth/me")).status_code == 401
    assert (await c.post("/api/v1/auth/tokens", json={"name": "denied", "scope": "admin"})).status_code == 401
    assert await ctx.auth.has_password()
    assert await ctx.store.kv_get("settings") == raw  # load does not silently rewrite recovery evidence
    for override, expected in [("none", 200), ("password", 401)]:
        ctx.config.auth_mode = override
        await ctx._apply_env_overrides()
        assert (await c.get("/api/v1/auth/me")).status_code == expected


@pytest.mark.parametrize("raw", [{"auth": None}, {"auth": []}, {"auth": {"mode": "oops"}}, [],
                                {"auth": {}, "ui": {"accent": "invalid"}}])
async def test_sec01_malformed_auth_fails_closed(rig, raw):
    c, ctx, _, _ = rig
    await protect(ctx)
    await ctx.store.kv_set("settings", raw)
    await ctx.settings.load()
    assert (await c.get("/api/v1/auth/me")).status_code == 401


async def test_sec02_passwordless_origin_and_bearer_scope(rig):
    c, ctx, _, _ = rig
    path = "/api/v1/settings"
    before = ctx.settings.current.model_dump()
    for origin in ["http://evil.example", "null", "https://127.0.0.1:21841", "http://[bad"]:
        r = await c.patch(path, headers={"Origin": origin}, json={"general": {"instance_name": "bad"}})
        assert r.status_code == 403
        assert ctx.settings.current.model_dump() == before
    for headers in [{}, {"Origin": "http://127.0.0.1:21841"}]:
        assert (await c.patch(path, headers=headers, json={"general": {"instance_name": "good"}})).status_code == 200
    _, token = await ctx.store.create_token("control", "control")
    headers = {"Authorization": f"Bearer {token}", "Origin": "http://evil.example"}
    assert (await c.post("/api/v1/events/ack-all", headers=headers)).status_code == 200
    assert (await c.patch(path, headers=headers, json={})).status_code == 403
    assert (await c.post("/api/v1/events/ack-all", headers={"Origin": "http://evil.example"})).status_code == 403


async def test_sec02_hosts_and_configured_cors(rig, monkeypatch):
    c, ctx, _, _ = rig
    assert (await c.get("/api/v1/meta", headers={"Host": "evil.example:21841"})).status_code == 400
    for host in ["localhost:21841", "192.168.20.3:21841", "10.0.0.3", "[::1]:21841", "[fd00::1]:21841"]:
        assert (await c.get("/api/v1/meta", headers={"Host": host})).status_code == 200
    for host in ["evil.local", "127.0.0.1@evil.example", "127.0.0.1/path", "127.0.0.1:bad", "0.0.0.0", "evil.example,localhost"]:
        assert (await c.get("/api/v1/meta", headers={"Host": host})).status_code == 400
    monkeypatch.setenv("BSMM_ALLOWED_HOSTS", "miner.example,custom.lan")
    cfg = RuntimeConfig(data_dir=ctx.config.data_dir, offline=True, cors_origins=["https://ui.example"])
    app = create_app(cfg, ctx=ctx)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://miner.example") as proxy:
        assert (await proxy.get("/api/v1/meta")).status_code == 200
        assert (await proxy.get("/api/v1/meta", headers={"Host": "custom.lan"})).status_code == 200
        r = await proxy.post("/api/v1/events/ack-all", headers={"Origin": "https://ui.example"})
        assert r.status_code == 403  # CORS read permission is not ambient write authority
        preflight = await proxy.options("/api/v1/events/ack-all", headers={
            "Origin": "https://ui.example", "Access-Control-Request-Method": "POST"})
        assert preflight.headers["access-control-allow-origin"] == "https://ui.example"


@pytest.mark.parametrize("kind", list(CHANNEL_CLASSES))
async def test_sec03_import_excludes_every_declared_channel_secret(rig, kind):
    c, ctx, _, _ = rig
    fields = CHANNEL_CLASSES[kind].fields
    config = {f.name: "SYNTHETIC_PRIVATE" if f.secret else "public-value" for f in fields}
    r = await c.post("/api/v1/system/import", json={"format": "bsmm-config-v1", "channels": [
        {"id": "imported", "kind": kind, "name": "imported", "enabled": True, "config": config,
         "secret": {"token": "SYNTHETIC_PRIVATE"}, "has_secret": True}]})
    assert r.status_code == 200
    row = await ctx.store.db.fetchone("SELECT config, secret_enc FROM channels WHERE id = ?", ("imported",))
    assert "SYNTHETIC_PRIVATE" not in row["config"]
    assert row["secret_enc"] is None
    assert not (await ctx.store.get_channel("imported")).enabled
    assert json.loads(row["config"]) == {f.name: "public-value" for f in fields if not f.secret}
    assert "SYNTHETIC_PRIVATE" not in (await c.get("/api/v1/system/export")).text
    await protect(ctx)
    _, token = await ctx.store.create_token("reader", "read")
    result = await c.get("/api/v1/notifications/channels", headers={"Authorization": f"Bearer {token}"})
    assert result.status_code == 200 and "SYNTHETIC_PRIVATE" not in result.text
    assert not result.json()["channels"][0]["has_secret"]


@pytest.mark.parametrize("bad", [{"kind": "unknown"}, {"kind": "telegram", "config": None}])
async def test_sec03_invalid_channel_import_has_no_partial_channel_writes(rig, bad):
    c, ctx, _, _ = rig
    r = await c.post("/api/v1/system/import", json={"format": "bsmm-config-v1", "channels": [
        {"id": "first", "kind": "telegram", "name": "first", "config": {"bot_token": "SYNTHETIC_PRIVATE"}},
        {"id": "bad", "name": "bad", **bad}]})
    assert r.status_code in (400, 422)
    assert await ctx.store.list_channels() == []


@pytest.mark.parametrize("path", ["/api/v1/auth/login", "/mcp"])
@pytest.mark.parametrize("length", [None, "1", str(MAX_BODY)])
async def test_sec04_receive_limit(rig, path, length):
    c, _, _, _ = rig
    body = json.dumps({"password": "unused", "padding": "x" * MAX_BODY}).encode()
    async def chunks():
        for i in range(0, len(body), 65536):
            yield body[i:i + 65536]
    headers = {"Content-Type": "application/json"}
    if length is not None:
        headers["Content-Length"] = length
    r = await c.post(path, content=chunks(), headers=headers)
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "too_large"


@pytest.mark.parametrize("size", [128, MAX_BODY])
async def test_sec04_at_or_below_limit_parses(rig, size):
    c, _, _, _ = rig
    body = b'{"password":"unused"}'
    body += b" " * (size - len(body))
    async def chunks():
        yield body[:32]
        yield body[32:]
    r = await c.post("/api/v1/auth/login", content=chunks(), headers={"Content-Type": "application/json"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "no_password"


@pytest.mark.parametrize("mode", ["token", "session-reset", "session-expire", "public", "none"])
@pytest.mark.parametrize("queued", [True, False])
async def test_sec05_open_stream_revalidates(rig, mode, queued):
    c, ctx, _, app = rig
    await protect(ctx)
    headers = []
    creds = None
    if mode == "token":
        tid, token = await ctx.store.create_token("stream", "read")
        headers = [(b"authorization", f"Bearer {token}".encode())]
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    elif mode.startswith("session"):
        sid = await ctx.store.create_session(100, None, "127.0.0.1")
        headers = [(b"cookie", f"bsmm_session={sid}".encode())]
    else:
        await ctx.settings.update({"auth": {"mode": "none" if mode == "none" else "password", "public_read": True}})
    async def receive():
        await asyncio.Event().wait()
    req = Request({"type": "http", "app": app, "method": "GET", "path": "/api/v1/stream", "headers": headers,
                   "client": ("127.0.0.1", 1), "server": ("127.0.0.1", 21841), "scheme": "http", "query_string": b""}, receive=receive)
    principal = await require("read")(req, creds)
    response = await stream(req, "event", ctx, principal)
    iterator = response.body_iterator
    pending = None
    try:
        assert b"event: hello" in await anext(iterator)
        ctx.bus.publish("event", {"marker": "authorized"})
        assert b"authorized" in await anext(iterator)
        pending = asyncio.create_task(anext(iterator))
        await asyncio.sleep(0)  # put the generator in its receive wait before the mutation
        if mode == "token":
            await ctx.store.delete_token(tid)
        elif mode == "session-reset":
            await ctx.auth.set_password("synthetic-new-password")
        elif mode == "session-expire":
            await ctx.store.db.execute("UPDATE sessions SET expires_at = 0")
        else:
            await ctx.settings.update({"auth": {"mode": "password", "public_read": False}})
        if queued:
            ctx.bus.publish("event", {"marker": "sensitive-after-revoke"})
        with pytest.raises(StopAsyncIteration):
            done, _ = await asyncio.wait({pending}, timeout=2)
            assert pending in done, "stream did not close within two seconds"
            await pending
    finally:
        if pending is not None and not pending.done():
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
        await iterator.aclose()
    assert ctx.bus.subscriber_count == 0


@pytest.mark.parametrize("valid", ["1BoatSLRHtKNngkdXEeobR76b53LETtpyT", "1111111111111111111114oLvT2",
                                        "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy", "mipcBbFg9gMiCh81Kj8tqqdgoZub1ZJRfn"])
async def test_sec07_canonical_base58_settings(rig, valid):
    c, ctx, _, _ = rig
    assert is_valid_address(valid)
    assert (await c.patch("/api/v1/settings", json={"mining": {"addresses": [valid]}})).status_code == 200
    malformed = valid[1:] if valid.startswith("1") else "1" + valid
    assert not is_valid_address(malformed)
    assert not is_valid_address("1" + valid)
    r = await c.patch("/api/v1/settings", json={"mining": {"addresses": [malformed]}})
    assert r.status_code == 422
    assert ctx.settings.current.mining.addresses == [valid]


def test_sec08_simulator_capture_redacts_embedded_identifiers():
    sample = CgminerSim(seed=1).reply("estats")
    sample["note"] = "BC1QAR0SRRR7XFKVY5L643LYDNW9RE59GTZZWF5MDQ"
    original = sample["STATS"][0]["MM ID0"]
    out = redact(sample)
    assert "0123456789abcdef" not in json.dumps(out)
    assert out["note"] == "<address>"
    assert out["STATS"][0]["MM ID0"] == original.replace("DNA[0123456789abcdef]", "DNA[<redacted>]")
    assert sample["STATS"][0]["MM ID0"] == original
    assert redact("status Temp[38] GHSspd[3900.0]") == "status Temp[38] GHSspd[3900.0]"


async def test_sec09_secret_rotation_rebuilds_selected_rpc(rig):
    c, ctx, _, _ = rig
    seen = []
    async def rpc(request):
        seen.append(request.headers.get("authorization"))
        body = json.loads(request.content)
        return httpx.Response(200, json={"result": 1, "error": None, "id": body["id"]})
    await ctx.http.aclose()
    ctx.http = httpx.AsyncClient(transport=httpx.MockTransport(rpc))
    ctx.network.http = ctx.http
    for name in ["selected", "neighbor"]:
        await ctx.store.save_source(Source(id=name, kind="bitcoin_core", name=name, url="http://127.0.0.1:1"),
                                    secret={"rpc_user": "test", "rpc_password": "old"})
    await ctx.network.reload_sources()
    old = ctx.network._pollers["selected"]
    neighbor = ctx.network._pollers["neighbor"]
    await old.impl.rpc.call("getblockcount")
    r = await c.patch("/api/v1/sources/selected", json={"secret": {"rpc_user": "test", "rpc_password": "new"}})
    assert r.status_code == 200
    new = ctx.network._pollers["selected"]
    assert new is not old
    assert ctx.network._pollers["neighbor"] is neighbor
    await new.impl.rpc.call("getblockcount")
    assert seen == [httpx.BasicAuth("test", value)._auth_header for value in ["old", "new"]]
    await ctx.network.reload_sources()
    assert ctx.network._pollers["selected"] is new
    assert (await c.patch("/api/v1/sources/selected", json={"secret": {}})).status_code == 200
    assert ctx.network._pollers["selected"].impl.secret == {}


@pytest.mark.parametrize("section", ["auth", "energy", "ui", "polling"])
@pytest.mark.parametrize("value", [None, [], "text", 1])
async def test_sec10_nested_shapes_rejected_without_effects(rig, section, value):
    c, ctx, _, _ = rig
    before = ctx.settings.current.model_dump()
    patch = {"energy": {"price_per_kwh": 0.25}, section: value}
    r = await c.patch("/api/v1/settings", json=patch)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"
    assert ctx.settings.current.model_dump() == before
    assert not await ctx.store.kv_get("insight.energy_confirmed")
    assert (await c.patch("/api/v1/settings", json={"energy": {"price_per_kwh": 0.25}})).status_code == 200
    assert await ctx.store.kv_get("insight.energy_confirmed") is True
    assert ctx.settings.current.energy.psu_overhead_pct == before["energy"]["psu_overhead_pct"]


@pytest.mark.parametrize("started", [True, False])
async def test_sec11_shutdown_awaits_discovery_before_resources_close(rig, monkeypatch, started):
    _, ctx, _, _ = rig
    from bsmm.engine import discovery
    entered = asyncio.Event()
    cancelled = []
    async def synthetic_tcp(host, port, timeout):
        assert host == "127.0.0.1"
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            assert not ctx.http.is_closed
            assert await ctx.store.db.scalar("SELECT 1") == 1
            cancelled.append(port)
    monkeypatch.setattr(discovery, "tcp_open", synthetic_tcp)
    monkeypatch.setattr(discovery, "own_ipv4_addresses", set)
    job = ctx.discovery.start(["127.0.0.1/32"], include_sources=False)
    if started:
        await asyncio.wait_for(entered.wait(), 1)
    try:
        await ctx.stop()
        assert job._task.done()
        assert job.status == "cancelled" and job.finished_at is not None
        assert ctx.http.is_closed
        if started:
            assert len(cancelled) == len(discovery.SWEEP_PORTS)
    finally:
        if not job._task.done():
            ctx.discovery.cancel(job.id)
            await asyncio.gather(job._task, return_exceptions=True)


@pytest.mark.parametrize("override, expected", [(None, 401), ("none", 200), ("password", 401)])
async def test_sec01_restart_recovers_preferences_not_auth(tmp_path, override, expected):
    cfg = RuntimeConfig(data_dir=tmp_path, offline=True, no_update_check=True, auth_mode=None, admin_password=None)
    ctx = await AppContext.create(cfg, http=httpx.AsyncClient(transport=MultiHostTransport({})))
    await protect(ctx)
    raw = ctx.settings.current.model_dump()
    raw["polling"]["interval_s"] = -1
    await ctx.store.kv_set("settings", raw)
    await ctx.stop()
    cfg.auth_mode = override
    restarted = await AppContext.create(cfg, http=httpx.AsyncClient(transport=MultiHostTransport({})))
    try:
        await restarted.start()
        app = create_app(ctx=restarted)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as c:
            assert (await c.get("/api/v1/auth/me")).status_code == expected
            if expected == 401:
                assert (await c.post("/api/v1/auth/tokens", json={"name": "denied"})).status_code == 401
                assert (await c.post("/api/v1/auth/login", json={"password": "synthetic-test-password"})).status_code == 200
                assert (await c.get("/api/v1/auth/me")).status_code == 200
        assert await restarted.auth.has_password()
    finally:
        await restarted.stop()


async def test_sec02_mcp_origin_cannot_bypass_rest_guard(rig):
    c, ctx, _, app = rig
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
        "name": "update_settings", "arguments": {"patch": {"general": {"instance_name": "changed"}}}}}
    headers = {"Origin": "http://evil.example", "Accept": "application/json, text/event-stream"}
    async with app.router.lifespan_context(app):
        denied = await c.post("/mcp", json=payload, headers=headers)
        assert denied.status_code == 403
        assert ctx.settings.current.general.instance_name != "changed"
        _, token = await ctx.store.create_token("admin", "admin")
        headers["Authorization"] = f"Bearer {token}"
        allowed = await c.post("/mcp", json=payload, headers=headers)
        assert allowed.status_code == 200 and not allowed.json()["result"].get("isError")
        assert ctx.settings.current.general.instance_name == "changed"


@pytest.mark.parametrize("length", [str(MAX_BODY + 1), "9" * 5000], ids=["over-limit", "long-header"])
async def test_sec04_declared_oversize_rejects_without_receiving(rig, length):
    _, _, _, app = rig
    messages = []
    async def receive():
        pytest.fail("oversize header must be rejected before receive")
    async def send(message):
        messages.append(message)
    scope = {"type": "http", "method": "POST", "path": "/api/v1/auth/login", "headers": [
        (b"host", b"localhost"), (b"content-length", length.encode())], "scheme": "http", "query_string": b""}
    await app(scope, receive, send)
    assert messages[0]["status"] == 413
    assert json.loads(messages[1]["body"])["error"]["code"] == "too_large"


async def test_sec04_disconnect_during_receive_never_parses(rig):
    _, ctx, _, app = rig
    sent = []
    messages = iter([{"type": "http.request", "body": b'{"general":', "more_body": True},
                     {"type": "http.disconnect"}])
    async def receive():
        return next(messages)
    async def send(message):
        sent.append(message)
    await app({"type": "http", "method": "PATCH", "path": "/api/v1/settings", "headers": [
        (b"host", b"localhost"), (b"content-type", b"application/json")], "scheme": "http", "query_string": b""}, receive, send)
    assert not sent
    assert ctx.settings.current.general.instance_name == "My solo mining fleet"


async def test_sec05_socket_stream_closes_on_revoke(rig):
    from tests.live import serve
    _, ctx, _, app = rig
    await protect(ctx)
    tid, token = await ctx.store.create_token("socket-reader", "read")
    async with (
        serve(app) as base,
        httpx.AsyncClient(timeout=3, trust_env=False) as c,
        c.stream("GET", f"{base}/api/v1/stream?topics=event", headers={"Authorization": f"Bearer {token}"}) as response,
    ):
        assert response.status_code == 200
        lines = response.aiter_lines()
        assert await anext(lines) == "event: hello"
        await ctx.store.delete_token(tid)
        ctx.bus.publish("event", {"marker": "not-authorized"})
        remaining = [line async for line in lines]
        assert not any("not-authorized" in line for line in remaining)
    assert ctx.bus.subscriber_count == 0


async def test_sec09_poll_inflight_does_not_restore_old_credentials(rig, caplog):
    from bsmm.sim.bitcoin_core import FakeBitcoinCore
    c, ctx, _, _ = rig
    node = FakeBitcoinCore(user="test", password="SYNTHETIC_OLD")
    transport = httpx.ASGITransport(app=node.app())
    entered, release = asyncio.Event(), asyncio.Event()
    hold = False
    async def rpc(request):
        if hold and request.headers["authorization"] == httpx.BasicAuth("test", "SYNTHETIC_OLD")._auth_header:
            entered.set()
            await release.wait()
        return await transport.handle_async_request(request)
    await ctx.http.aclose()
    ctx.http = httpx.AsyncClient(transport=httpx.MockTransport(rpc))
    ctx.network.http = ctx.http
    await ctx.store.save_source(Source(id="selected", kind="bitcoin_core", name="node", url="http://127.0.0.1"),
                                secret={"rpc_user": "test", "rpc_password": "SYNTHETIC_OLD"})
    await ctx.network.reload_sources()
    old = ctx.network._pollers["selected"]
    await ctx.network._poll(old)
    assert old.health.ok
    hold = True
    pending = asyncio.create_task(ctx.network._poll(old))
    try:
        await asyncio.wait_for(entered.wait(), 1)
        node.password = "SYNTHETIC_NEW"
        result = await c.patch("/api/v1/sources/selected", json={"secret": {"rpc_user": "test", "rpc_password": "SYNTHETIC_NEW"}})
        assert result.status_code == 200
        new = ctx.network._pollers["selected"]
        assert new is not old
        await ctx.network._poll(new)
        assert new.health.ok and new.snapshot is not None
    finally:
        release.set()
        await pending
    assert ctx.network._pollers["selected"] is new
    assert "SYNTHETIC_NEW" not in caplog.text and "SYNTHETIC_OLD" not in caplog.text


async def test_sec11_shutdown_waits_for_cancel_cleanup_and_refuses_new_jobs(rig, monkeypatch):
    from bsmm.engine import discovery
    _, ctx, _, _ = rig
    entered, cancelling, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
    async def tcp(host, port, timeout):
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelling.set()
            await release.wait()
            assert not ctx.http.is_closed
    monkeypatch.setattr(discovery, "tcp_open", tcp)
    monkeypatch.setattr(discovery, "own_ipv4_addresses", set)
    job = ctx.discovery.start(["127.0.0.1/32"], include_sources=False)
    await asyncio.wait_for(entered.wait(), 1)
    stopped = asyncio.create_task(ctx.stop())
    try:
        await asyncio.wait_for(cancelling.wait(), 1)
        assert not stopped.done() and not ctx.http.is_closed
        assert await ctx.store.db.scalar("SELECT 1") == 1
        with pytest.raises(RuntimeError, match="shutting down"):
            ctx.discovery.start(["127.0.0.1/32"], include_sources=False)
    finally:
        release.set()
        # Baseline has no discovery stop; explicit cleanup keeps this regression isolated there too.
        if not job._task.done():
            ctx.discovery.cancel(job.id)
        await asyncio.gather(job._task, stopped, return_exceptions=True)
    assert job._task.done() and ctx.http.is_closed


async def test_sec01_invalid_json_is_not_first_run(rig):
    c, ctx, _, _ = rig
    await protect(ctx)
    await ctx.store.db.execute("UPDATE kv SET value = ? WHERE key = ?", ('{"broken":', "settings"))
    await ctx.settings.load()
    assert (await c.get("/api/v1/auth/me")).status_code == 401
    assert await ctx.auth.has_password()


async def test_sec11_pending_cancelled_jobs_are_retained_until_drained(rig, monkeypatch):
    from bsmm.engine import discovery
    _, ctx, _, _ = rig
    monkeypatch.setattr(discovery, "own_ipv4_addresses", set)
    entered, release = asyncio.Event(), asyncio.Event()
    async def run(job, *args):
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            await release.wait()
    monkeypatch.setattr(ctx.discovery, "_run", run)
    jobs = []
    try:
        for _ in range(7):
            entered.clear()
            job = ctx.discovery.start(["127.0.0.1/32"], include_sources=False)
            jobs.append(job)
            await asyncio.wait_for(entered.wait(), 1)
            ctx.discovery.cancel(job.id)
            await asyncio.sleep(0)
        assert all(job.id in ctx.discovery.jobs for job in jobs)
    finally:
        release.set()
        await asyncio.gather(*(job._task for job in jobs), return_exceptions=True)
