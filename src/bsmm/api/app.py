"""FastAPI application factory."""

from __future__ import annotations

import ipaddress
import logging
import socket
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from bsmm import __version__
from bsmm.api import errors
from bsmm.api.deps import SAFE_METHODS, _bearer, check_browser_origin, resolve_principal
from bsmm.api.routes_alerts import router as alerts_router
from bsmm.api.routes_chain import router as chain_router
from bsmm.api.routes_core import router as core_router
from bsmm.api.routes_fleet import router as fleet_router
from bsmm.api.routes_ops import ops_router
from bsmm.api.routes_ops import router as ops_api_router
from bsmm.config import RuntimeConfig
from bsmm.context import AppContext

log = logging.getLogger(__name__)
WEB_DIR = Path(__file__).resolve().parent.parent / "web"
MAX_BODY = 4 * 1024 * 1024


class BodyLimitMiddleware:
    """Bound actual received bytes before any REST or MCP body parser runs."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        length = headers.get(b"content-length", b"")
        significant = length.lstrip(b"0")
        oversized = length.isdigit() and (len(significant) > len(str(MAX_BODY)) or int(significant or b"0") > MAX_BODY)
        body = bytearray()
        while not oversized:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > MAX_BODY:
                oversized = True
                break
            body.extend(chunk)
            if not message.get("more_body", False):
                break
        if oversized:
            response = JSONResponse(errors.body(413, "too_large", "That request is too large."), status_code=413)
            await response(scope, receive, send)
            return
        delivered = False

        async def replay() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


_LAN_HOST_NETWORKS = tuple(ipaddress.ip_network(cidr) for cidr in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10", "169.254.0.0/16", "fc00::/7", "fe80::/10",
))


def _allowed_host(value: str, names: set[str]) -> bool:
    # Do not resolve untrusted names: a DNS answer is not Host authorization.
    if not value or any(c in value for c in "/\\@?#, \t\r\n"):
        return False
    try:
        parsed = urlsplit("//" + value)
        host = parsed.hostname
        _ = parsed.port  # reject malformed ports, including on otherwise allowed names
        if not host:
            return False
        if host.lower().rstrip(".") in names:
            return True
        ip = ipaddress.ip_address(host)
        return ip.is_loopback or any(ip in network for network in _LAN_HOST_NETWORKS)
    except ValueError:
        return False

DESCRIPTION = """
Dashboard, monitoring and control for **solo Bitcoin miners**. Discovers miners on your network, watches
your node and pool, computes the odds of finding a block, and alerts you.

**New here (human or AI agent)?** Call `GET /api/v1/meta`, then read `GET /api/v1/agent/guide` or `/llms.txt`.
Errors always look like `{"error": {"code", "message", "hint", "status"}}`.

**Auth:** when a password is set, send `Authorization: Bearer <token>`. Scopes: `read` < `control` < `admin`.
"""

TAGS = [
    {"name": "system", "description": "Health, version, diagnostics, backup, updates."},
    {"name": "fleet", "description": "Fleet totals, history, insights and the live stream."},
    {"name": "devices", "description": "Your miners: add, rename, read, control."},
    {"name": "discovery", "description": "Find miners and your node/pool on the network."},
    {"name": "bitcoin", "description": "Network state, your node, pool, odds, blocks."},
    {"name": "sources", "description": "Configure the node, pool and public data sources."},
    {"name": "alerts", "description": "Alert rules, active alerts and the activity log."},
    {"name": "notifications", "description": "Where alerts are sent (ntfy, Telegram, Discord, email...)."},
    {"name": "settings", "description": "Preferences, polling, energy price, safety switches."},
    {"name": "auth", "description": "Password, sessions and API tokens."},
    {"name": "agents", "description": "Machine-readable guidance for AI agents."},
    {"name": "demo", "description": "Only in demo mode."},
]

CSP = (
    "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; "
    "font-src 'self' data:; manifest-src 'self'; worker-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
)


def create_app(config: RuntimeConfig | None = None, *, ctx: AppContext | None = None) -> FastAPI:
    """Build the app. Pass ``ctx`` (tests) to use an existing context whose lifecycle you manage yourself."""
    config = config or (ctx.config if ctx else RuntimeConfig())
    owns_ctx = ctx is None
    hostname = socket.gethostname().lower().rstrip(".")
    host_names = {"localhost", "bsmm.internal", hostname, hostname.split(".")[0], hostname.split(".")[0] + ".local"}
    host_names.update(h.lower().rstrip(".") for h in config.allowed_hosts if h != "*")
    if config.host not in ("0.0.0.0", "::", "*"):
        host_names.add(config.host.lower().rstrip("."))

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        context = ctx
        if owns_ctx:
            context = await AppContext.create(config)
            if config.demo:
                from bsmm.demo import seed_demo

                await seed_demo(context)
            await context.start()
        app.state.ctx = context
        async with AsyncExitStack() as stack:
            mcp_lifespan = getattr(app.state, "mcp_lifespan", None)
            if mcp_lifespan is not None:  # the MCP session manager needs its own lifespan running
                await stack.enter_async_context(mcp_lifespan(app.state.mcp_asgi))
            try:
                yield
            finally:
                if owns_ctx and context is not None:
                    await context.stop()

    app = FastAPI(
        title="Bitcoin Solo Miner Monitor API",
        version=__version__,
        description=DESCRIPTION,
        openapi_tags=TAGS,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url=None,
        license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
        contact={"name": "Project issues", "url": "https://github.com/smokeysrh/bitcoin-solo-miner-monitor/issues"},
    )
    if ctx is not None:
        app.state.ctx = ctx
    errors.install(app)

    if config.cors_origins:
        app.add_middleware(CORSMiddleware, allow_origins=config.cors_origins, allow_credentials=True,
                           allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"], allow_headers=["Authorization", "Content-Type", "X-API-Key"])
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    @app.middleware("http")
    async def guard(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        hosts = request.headers.getlist("host")
        if len(hosts) != 1 or not _allowed_host(hosts[0], host_names):
            return JSONResponse(errors.body(400, "invalid_host", "This server name is not allowed.",
                                           "Use its LAN IP or configure BSMM_ALLOWED_HOSTS with exact proxy/DNS names."), status_code=400)
        if request.method not in SAFE_METHODS and "origin" in request.headers:
            principal = await resolve_principal(request, await _bearer(request))
            try:
                check_browser_origin(request, principal)
            except errors.ApiError as exc:
                return JSONResponse(errors.body(exc.status, exc.code, exc.message), status_code=exc.status)
        started = time.perf_counter()
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        response = await call_next(request)
        response.headers["X-Request-Id"] = rid
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        path = request.url.path
        if response.headers.get("content-type", "").startswith("text/html") and not path.startswith(("/docs", "/redoc")):
            response.headers["Content-Security-Policy"] = CSP
        if path.startswith("/api/") and "cache-control" not in response.headers:
            response.headers["Cache-Control"] = "no-store"
        if log.isEnabledFor(logging.DEBUG):
            log.debug("%s %s -> %s in %.1f ms", request.method, path, response.status_code, (time.perf_counter() - started) * 1000)
        return response

    app.include_router(core_router, prefix="/api/v1")
    app.include_router(fleet_router, prefix="/api/v1")
    app.include_router(chain_router, prefix="/api/v1")
    app.include_router(alerts_router, prefix="/api/v1")
    app.include_router(ops_api_router, prefix="/api/v1")
    app.include_router(ops_router)

    _mount_mcp(app)
    if config.serve_ui:
        _mount_ui(app)
    app.add_middleware(BodyLimitMiddleware)
    return app


def _mount_mcp(app: FastAPI) -> None:
    try:
        from bsmm.mcp_server import build_http_app
    except Exception:  # the MCP SDK is optional at import time; the CLI reports a clear message
        log.info("MCP endpoint not mounted (SDK unavailable)")
        return
    try:
        entry = build_http_app(app)
        # a plain route (not a Mount) so that the exact URL /mcp works without a redirect
        app.add_route("/mcp", entry, methods=["GET", "POST", "DELETE"], include_in_schema=False)
    except Exception:
        log.exception("could not mount the MCP endpoint")


def _mount_ui(app: FastAPI) -> None:
    index = WEB_DIR / "index.html"
    if not index.exists():

        @app.get("/", include_in_schema=False)
        async def no_ui() -> HTMLResponse:
            return HTMLResponse(
                "<!doctype html><meta charset=utf-8><title>Solo Miner Monitor</title>"
                "<body style='font:16px system-ui;background:#0b0e14;color:#e6e8ee;max-width:42rem;margin:4rem auto;padding:0 1rem'>"
                "<h1>Solo Miner Monitor</h1><p>The API is running, but the web interface was not built into this install.</p>"
                "<p>Developers: <code>cd web &amp;&amp; npm install &amp;&amp; npm run build</code>. Everyone else: use the release package or Docker image.</p>"
                "<p><a style='color:#f7931a' href='/docs'>API docs</a> &middot; <a style='color:#f7931a' href='/api/v1/meta'>/api/v1/meta</a> &middot; "
                "<a style='color:#f7931a' href='/llms.txt'>llms.txt</a></p></body>"
            )

        return
    assets = WEB_DIR / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    reserved = ("api/", "docs", "openapi.json", "metrics", "llms.txt", "mcp")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str) -> Response:
        if path.startswith(reserved):
            return JSONResponse(errors.body(404, "not_found", "No such endpoint.", "See /openapi.json."), status_code=404)
        candidate = (WEB_DIR / path).resolve()
        if path and candidate.is_file() and WEB_DIR.resolve() in candidate.parents:
            if path.startswith("assets/"):
                cache = "public, max-age=31536000, immutable"  # file names carry a content hash
            elif path in ("sw.js", "manifest.webmanifest", "theme-init.js"):
                cache = "no-cache"  # must pick up a new release immediately
            else:
                cache = "public, max-age=3600"
            return FileResponse(candidate, headers={"Cache-Control": cache})
        if "." in path.rsplit("/", 1)[-1]:
            # a missing file (an old hashed asset, a typo) must 404, not come back as the app's HTML page
            return JSONResponse(errors.body(404, "not_found", "No such file."), status_code=404)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
