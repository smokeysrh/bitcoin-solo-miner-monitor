"""System, authentication and settings endpoints."""

from __future__ import annotations

import os
import platform
import shutil
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from bsmm import __version__
from bsmm.api.deps import client_ip, get_ctx, require
from bsmm.api.errors import ApiError, bad_request, not_found
from bsmm.auth import COOKIE_NAME, SESSION_TTL_S, Principal
from bsmm.context import AppContext
from bsmm.engine.insights import build_insights, dismiss
from bsmm.models import AlertRule, Channel, Device, Source
from bsmm.net import local_ipv4_networks
from bsmm.settings import Settings
from bsmm.updates import check_for_update

router = APIRouter()


# ------------------------------------------------------------------------------------------ meta / health


@router.get("/health", tags=["system"], operation_id="getHealth", summary="Liveness probe (no login needed)")
async def health(ctx: AppContext = Depends(get_ctx)) -> dict[str, Any]:
    return {"status": "ok", "version": __version__, "uptime_s": int(time.time() - ctx.started_at)}


@router.get(
    "/meta",
    tags=["system"],
    operation_id="getMeta",
    summary="What this server is, how to authenticate, and how far setup has got (no login needed)",
    description="Start here. Tells a client (or an AI agent) the app version, whether a login is required, whether this is a demo, "
    "and a checklist of what is still unconfigured. Contains no secrets and no miner data.",
)
async def meta(request: Request, ctx: AppContext = Depends(get_ctx)) -> dict[str, Any]:
    s = ctx.settings.current
    sources = [h for h in ctx.network.state.sources if not h.implicit]
    base = str(request.base_url).rstrip("/")
    return {
        "app": "bitcoin-solo-miner-monitor",
        "version": __version__,
        "api_version": "v1",
        "demo": ctx.config.demo,
        "instance_name": s.general.instance_name,
        "auth": {"mode": s.auth.mode, "password_set": await ctx.auth.has_password(), "public_read": s.auth.public_read,
                 "token_header": "Authorization: Bearer <token>"},
        "setup": {
            "onboarding_done": s.general.onboarding_done,
            "devices": len(ctx.fleet.runtimes),
            "has_node_or_pool": bool(sources),
            "has_notification_channel": bool([c for c in await ctx.store.list_channels() if c.enabled]),
            "network_data": ctx.network.state.available,
        },
        "ui": {"theme": s.ui.theme, "accent": s.ui.accent},
        "links": {
            "openapi": f"{base}/openapi.json",
            "docs": f"{base}/docs",
            "llms_txt": f"{base}/llms.txt",
            "agent_guide": f"{base}/api/v1/agent/guide",
            "mcp": f"{base}/mcp",
            "metrics": f"{base}/metrics",
        },
    }


@router.get("/system/info", tags=["system"], operation_id="getSystemInfo", summary="Version, platform and storage details")
async def system_info(ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("read"))) -> dict[str, Any]:
    cfg = ctx.config
    size = cfg.db_path.stat().st_size if cfg.db_path.exists() else 0
    return {
        "version": __version__, "python": sys.version.split()[0], "platform": platform.platform(),
        "uptime_s": int(time.time() - ctx.started_at), "data_dir": str(cfg.data_dir), "db_size_bytes": size,
        "schema_version": await ctx.store.db.schema_version(), "devices": len(ctx.fleet.runtimes),
        "stream_subscribers": ctx.bus.subscriber_count, "demo": cfg.demo, "offline_mode": cfg.offline,
    }


@router.get(
    "/system/diagnostics",
    tags=["system"],
    operation_id="getDiagnostics",
    summary="Self-check with plain-English results (what `bsmm doctor` prints)",
    description="Paste this into a bug report. It contains device IP addresses but no passwords, tokens or payout addresses.",
)
async def diagnostics(ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("read"))) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(id_: str, ok: bool | None, message: str, fix: str | None = None) -> None:
        checks.append({"id": id_, "status": "pass" if ok else ("warn" if ok is None else "fail"), "message": message, **({"fix": fix} if fix and not ok else {})})

    try:
        await ctx.store.db.scalar("SELECT 1")
        check("database", True, "The database is working.")
    except Exception as e:  # pragma: no cover
        check("database", False, f"The database failed: {e}", "Check the data folder's permissions and free space.")
    free = shutil.disk_usage(ctx.config.data_dir if ctx.config.data_dir.exists() else Path("."))
    check("disk", free.free > 200 * 1024 * 1024, f"{free.free / 1e9:.1f} GB free where the data is stored.", "Free some disk space.")
    views = ctx.fleet.views()
    online = [v for v in views if v.status.value in ("online", "degraded", "paused")]
    if not views:
        check("miners", None, "No miners are being monitored yet.", "Run `bsmm discover` or open the app and choose 'Scan my network'.")
    else:
        check("miners", len(online) == len(views), f"{len(online)} of {len(views)} miner(s) are answering.",
              "See the offline miners below; check power, WiFi and their IP address.")
    net = ctx.network.state
    check("network-data", net.available, "Network difficulty and block height are known." if net.available else "Network difficulty is unknown, so odds cannot be shown.",
          "Add a node/pool in Settings > Data sources, or allow public data (mempool.space).")
    nodes = [h for h in net.sources if h.kind == "bitcoin_core"]
    if nodes:
        check("node", all(h.ok for h in nodes), "Your Bitcoin node answers." if all(h.ok for h in nodes) else "Your Bitcoin node does not answer.", "Check its address and RPC login.")
    channels = [c for c in await ctx.store.list_channels() if c.enabled]
    check("notifications", True if channels else None, f"{len(channels)} notification channel(s) set up." if channels else "No notification channel is set up (you will only see alerts on the dashboard).",
          "Add ntfy, Telegram, Discord or email in Settings > Notifications.")
    if os.name == "posix" and ctx.config.key_path.exists():
        mode = ctx.config.key_path.stat().st_mode & 0o777
        check("secret-key", mode & 0o077 == 0, "The encryption key file is private." if mode & 0o077 == 0 else f"The encryption key file is readable by other users (mode {mode:o}).",
              f"Run: chmod 600 {ctx.config.key_path}")
    check("auth", True if ctx.settings.current.auth.mode == "password" else None,
          "A password protects the dashboard." if ctx.settings.current.auth.mode == "password" else "No password: anyone on the network can use this dashboard.",
          "Set one in Settings > Security.")
    return {
        "version": __version__, "python": sys.version.split()[0], "platform": platform.platform(),
        "data_dir": str(ctx.config.data_dir), "listening": f"{ctx.config.host}:{ctx.config.port}",
        "lan_networks": [str(n) for n in local_ipv4_networks()], "checks": checks,
        "ok": not any(c["status"] == "fail" for c in checks),
        "devices": [{"id": v.id, "name": v.name, "host": v.host, "status": v.status.value, "reason": v.status_reason, "last_error": v.last_error,
                     "model": v.display_model, "firmware": v.firmware} for v in views],
        "sources": [h.model_dump() for h in net.sources],
    }


@router.get("/system/update", tags=["system"], operation_id="getUpdateStatus", summary="Is a newer release available? (cached for a day)")
async def update_status(ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("read"))) -> dict[str, Any]:
    if ctx.config.offline or ctx.config.no_update_check or ctx.config.demo:
        return {"current": __version__, "latest": None, "update_available": False, "disabled": True}
    return await check_for_update(ctx.store, ctx.http)


@router.post("/system/update/check", tags=["system"], operation_id="checkForUpdate", summary="Check GitHub for a newer release now")
async def update_check(ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("control"))) -> dict[str, Any]:
    if ctx.config.offline or ctx.config.no_update_check or ctx.config.demo:
        raise ApiError(409, "disabled", "Update checks are switched off (offline / no-update-check mode).")
    return await check_for_update(ctx.store, ctx.http, force=True)


@router.get("/system/backup", tags=["system"], operation_id="downloadBackup", summary="Download a consistent copy of the database (admin)",
            description="The copy holds encrypted secrets; to restore on another machine you also need that machine to have this one's secret.key.")
async def backup(background: BackgroundTasks, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("admin"))) -> FileResponse:
    tmp = Path(tempfile.mkdtemp(prefix="bsmm-backup-")) / f"bsmm-backup-{datetime.now():%Y%m%d-%H%M%S}.db"
    await ctx.store.backup_to(tmp)
    background.add_task(shutil.rmtree, tmp.parent, True)
    return FileResponse(tmp, media_type="application/octet-stream", filename=tmp.name)


@router.get("/system/export", tags=["system"], operation_id="exportConfig", summary="Export miners, settings, alert rules, channels and sources as JSON (secrets excluded)")
async def export_config(ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("admin"))) -> dict[str, Any]:
    return {
        "format": "bsmm-config-v1", "exported_at": time.time(), "app_version": __version__,
        "settings": ctx.settings.current.model_dump(),
        "devices": [d.model_dump(mode="json") for d in await ctx.store.list_devices()],
        "rules": [r.model_dump(mode="json") for r in await ctx.store.list_rules()],
        "channels": [c.model_dump(mode="json") for c in await ctx.store.list_channels()],
        "sources": [s.model_dump(mode="json") for s in await ctx.store.list_sources()],
        "note": "Passwords, tokens and webhook URLs are never exported. Re-enter them after importing.",
    }


class ImportBody(BaseModel):
    format: str
    settings: dict[str, Any] | None = None
    devices: list[dict[str, Any]] = Field(default_factory=list)
    rules: list[dict[str, Any]] = Field(default_factory=list)
    channels: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/system/import", tags=["system"], operation_id="importConfig", summary="Import a config export (merges; never overwrites existing miners)")
async def import_config(body: ImportBody, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("admin"))) -> dict[str, Any]:
    if body.format != "bsmm-config-v1":
        raise bad_request("This is not a config export from this app.", "Use a file produced by GET /api/v1/system/export.")
    added = {"devices": 0, "rules": 0, "channels": 0, "sources": 0}
    if body.settings:
        await ctx.settings.update({k: v for k, v in body.settings.items() if k != "auth"})
    from bsmm.drivers.registry import device_info

    for raw in body.devices:
        dev = Device.model_validate(raw)
        if await ctx.store.find_device(device_info(dev)):
            continue
        await ctx.store.save_device(dev, create=True)
        ctx.fleet._spawn(dev)
        added["devices"] += 1
    existing_rules = {r.id for r in await ctx.store.list_rules()}
    for raw in body.rules:
        rule = AlertRule.model_validate(raw)
        if rule.id not in existing_rules:
            await ctx.store.save_rule(rule)
            added["rules"] += 1
    existing_ch = {c.id for c in await ctx.store.list_channels()}
    for raw in body.channels:
        ch = Channel.model_validate(raw)
        if ch.id not in existing_ch:
            ch.enabled = False  # it has no secret yet, so it cannot work until the user re-enters it
            await ctx.store.save_channel(ch, secret={})
            added["channels"] += 1
    existing_src = {s.id for s in await ctx.store.list_sources()}
    for raw in body.sources:
        src = Source.model_validate(raw)
        if src.id not in existing_src:
            src.enabled = False
            await ctx.store.save_source(src, secret={})
            added["sources"] += 1
    await ctx.network.reload_sources()
    return {"ok": True, "added": added, "note": "Channels and sources arrive switched off: re-enter their secrets, then enable them."}


# ------------------------------------------------------------------------------------------ insights


@router.get("/insights", tags=["fleet"], operation_id="getInsights", summary="Plain-language observations and suggestions")
async def insights(ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("read"))) -> dict[str, Any]:
    return {"insights": await build_insights(ctx)}


@router.post("/insights/{insight_id}/dismiss", tags=["fleet"], operation_id="dismissInsight", summary="Hide an insight")
async def insight_dismiss(insight_id: str, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("control"))) -> dict[str, bool]:
    await dismiss(ctx, insight_id)
    return {"ok": True}


# ------------------------------------------------------------------------------------------ settings


@router.get("/settings", tags=["settings"], operation_id="getSettings", summary="All settings (never contains secrets)")
async def get_settings(ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("read"))) -> Settings:
    return ctx.settings.current


@router.patch(
    "/settings",
    tags=["settings"],
    operation_id="updateSettings",
    summary="Change settings (partial update)",
    description='Send only what changes, for example `{"energy": {"price_per_kwh": 0.09}}`. Nested objects are merged; invalid values are rejected whole.',
)
async def patch_settings(patch: dict[str, Any], ctx: AppContext = Depends(get_ctx), principal: Principal = Depends(require("admin"))) -> Settings:
    if patch.get("auth", {}).get("mode") == "password" and not await ctx.auth.has_password():
        raise bad_request("Set a password first, then switch password protection on.", "POST /api/v1/auth/password")
    if "energy" in patch and "price_per_kwh" in patch["energy"]:
        await ctx.store.kv_set("insight.energy_confirmed", True)
    return await ctx.settings.update(patch)


# ------------------------------------------------------------------------------------------ auth


class LoginBody(BaseModel):
    password: str = Field(min_length=1, max_length=200)


class PasswordBody(BaseModel):
    new_password: str = Field(min_length=8, max_length=200)
    current_password: str | None = Field(None, max_length=200)
    enable: bool = Field(True, description="Also switch password protection on")


class TokenBody(BaseModel):
    name: str = Field(min_length=1, max_length=60, description="What this token is for, e.g. 'Hermes agent'")
    scope: str = Field("read", pattern="^(read|control|admin)$")
    expires_days: float | None = Field(None, gt=0, le=3650)


@router.post("/auth/login", tags=["auth"], operation_id="login", summary="Sign in with the dashboard password (sets a session cookie)")
async def login(body: LoginBody, request: Request, response: Response, ctx: AppContext = Depends(get_ctx)) -> dict[str, Any]:
    if not await ctx.auth.has_password():
        raise ApiError(409, "no_password", "No password is set.", "Set one with POST /api/v1/auth/password.")
    try:
        sid = await ctx.auth.login(body.password, client_ip(request), request.headers.get("user-agent"))
    except PermissionError as e:
        raise ApiError(429, "rate_limited", str(e), "Wait a little and try again.") from e
    if sid is None:
        raise ApiError(401, "bad_password", "That password is not right.")
    response.set_cookie(COOKIE_NAME, sid, httponly=True, samesite="lax", max_age=SESSION_TTL_S, secure=request.url.scheme == "https", path="/")
    return {"ok": True}


@router.post("/auth/logout", tags=["auth"], operation_id="logout", summary="Sign out")
async def logout(request: Request, response: Response, ctx: AppContext = Depends(get_ctx)) -> dict[str, bool]:
    sid = request.cookies.get(COOKIE_NAME)
    if sid:
        await ctx.store.delete_session(sid)
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/auth/me", tags=["auth"], operation_id="getMe", summary="Who am I, and what am I allowed to do?")
async def me(principal: Principal = Depends(require("read"))) -> dict[str, str]:
    return {"name": principal.name, "scope": principal.scope, "via": principal.via}


@router.post("/auth/password", tags=["auth"], operation_id="setPassword", summary="Set or change the dashboard password (admin)")
async def set_password(body: PasswordBody, request: Request, response: Response, ctx: AppContext = Depends(get_ctx),
                       principal: Principal = Depends(require("admin"))) -> dict[str, Any]:
    if await ctx.auth.has_password() and not (body.current_password and await ctx.auth.check_password(body.current_password)):
        raise ApiError(401, "bad_password", "The current password is not right.")
    await ctx.auth.set_password(body.new_password)
    if body.enable:
        await ctx.settings.update({"auth": {"mode": "password"}})
    sid = await ctx.store.create_session(SESSION_TTL_S, request.headers.get("user-agent"), client_ip(request))
    response.set_cookie(COOKIE_NAME, sid, httponly=True, samesite="lax", max_age=SESSION_TTL_S, secure=request.url.scheme == "https", path="/")
    return {"ok": True, "auth_mode": ctx.settings.current.auth.mode}


@router.get("/auth/tokens", tags=["auth"], operation_id="listTokens", summary="List API tokens (never shows the token itself)")
async def list_tokens(ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("admin"))) -> dict[str, Any]:
    return {"tokens": await ctx.store.list_tokens()}


@router.post("/auth/tokens", tags=["auth"], operation_id="createToken", summary="Create an API token for a script or AI agent (admin)",
             description="The token is returned **once**. Scopes: `read` (look), `control` (restart miners, scan, change pools), `admin` (settings, tokens).")
async def create_token(body: TokenBody, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("admin"))) -> dict[str, Any]:
    exp = time.time() + body.expires_days * 86400 if body.expires_days else None
    token_id, token = await ctx.store.create_token(body.name, body.scope, exp)
    return {"id": token_id, "name": body.name, "scope": body.scope, "token": token, "expires_at": exp,
            "usage": f"Authorization: Bearer {token}", "warning": "Copy it now; it cannot be shown again."}


@router.delete("/auth/tokens/{token_id}", tags=["auth"], operation_id="deleteToken", summary="Revoke a token")
async def delete_token(token_id: str, ctx: AppContext = Depends(get_ctx), _: Principal = Depends(require("admin"))) -> dict[str, bool]:
    if not await ctx.store.delete_token(token_id):
        raise not_found("That token")
    return {"ok": True}
