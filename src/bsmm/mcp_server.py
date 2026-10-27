"""Model Context Protocol server: lets an AI agent operate the app with typed tools.

Every tool is a thin wrapper over the REST API (so there is exactly one implementation of every
behaviour and one set of permission checks). Two ways to run it:

* embedded in the web server at ``/mcp`` (streamable HTTP; the agent's bearer token is forwarded),
* ``bsmm mcp --url http://host:8420 --token ...`` over stdio, for MCP clients that spawn a process.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from typing import Any, Protocol

import httpx
from fastapi import FastAPI
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp_types import ToolAnnotations

from bsmm import __version__
from bsmm.agent_docs import agent_guide

READ = ToolAnnotations(read_only_hint=True, open_world_hint=False)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False)
DESTRUCTIVE = ToolAnnotations(read_only_hint=False, destructive_hint=True, open_world_hint=False)

INSTRUCTIONS = """\
This server controls a self-hosted dashboard for people who solo mine Bitcoin with ASIC miners.

Start with get_overview (fleet totals, odds of finding a block, alerts). To set a user up from scratch:
scan_network -> add_discovered_miners -> configure_source (their node/pool) -> create_notification_channel -> update_settings (electricity price).
Never guess a user's node credentials, wallet address or passwords: ask them. Bulk actions preview by default: show the
preview to the user before applying with dry_run=false. Restarting a miner pauses hashing for about a minute.
All hashrates are in H/s (fields ending _hs); the odds of finding a block are tiny and that is normal for solo mining.
"""


class Backend(Protocol):
    async def call(self, headers: Mapping[str, str] | None, method: str, path: str, *, params: dict[str, Any] | None = None,
                   json_body: Any = None) -> Any: ...


class ApiProblem(ToolError):
    """Raised inside a tool; the message goes back to the model, so it explains what to do next."""


def _clean(params: dict[str, Any] | None) -> dict[str, Any] | None:
    return {k: v for k, v in (params or {}).items() if v is not None} or None


class HttpBackend:
    """Talks to a running server over the network (used by the stdio command)."""

    def __init__(self, url: str, token: str | None, *, client: httpx.AsyncClient | None = None) -> None:
        self.base = url.rstrip("/")
        self.token = token
        self.client = client or httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=5.0))

    async def call(self, headers: Mapping[str, str] | None, method: str, path: str, *, params: dict[str, Any] | None = None,
                   json_body: Any = None) -> Any:
        h = {"Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        try:
            resp = await self.client.request(method, f"{self.base}{path}", params=_clean(params), json=json_body, headers=h)
        except httpx.HTTPError as e:
            raise ApiProblem(f"Could not reach the server at {self.base} ({e.__class__.__name__}). Is it running, and is the address right?") from e
        return _unwrap(resp)


class AsgiBackend:
    """Calls the REST app in-process, forwarding the caller's credentials (used by the embedded /mcp endpoint)."""

    def __init__(self, app: FastAPI) -> None:
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://bsmm.internal", timeout=120.0)

    async def call(self, headers: Mapping[str, str] | None, method: str, path: str, *, params: dict[str, Any] | None = None,
                   json_body: Any = None) -> Any:
        fwd: dict[str, str] = {}
        for name in ("authorization", "x-api-key"):
            if headers and headers.get(name):
                fwd[name] = headers[name]
        resp = await self.client.request(method, path, params=_clean(params), json=json_body, headers=fwd)
        return _unwrap(resp)


def _unwrap(resp: httpx.Response) -> Any:
    try:
        data = resp.json()
    except ValueError:
        data = None
    if resp.status_code >= 400:
        err = (data or {}).get("error", {}) if isinstance(data, dict) else {}
        msg = err.get("message") or f"HTTP {resp.status_code}"
        hint = err.get("hint")
        raise ApiProblem(f"{msg} {hint}" if hint else msg)
    return data if data is not None else resp.text


def build_server(backend: Backend, *, name: str = "bitcoin-solo-miner-monitor") -> MCPServer:
    mcp = MCPServer(name=name, title="Bitcoin Solo Miner Monitor", instructions=INSTRUCTIONS, version=__version__)

    async def api(ctx: Context, method: str, path: str, *, params: dict[str, Any] | None = None, body: Any = None) -> Any:
        headers = None
        try:
            headers = ctx.headers
        except Exception:  # stdio transport has no request headers
            headers = None
        return await backend.call(headers, method, path, params=params, json_body=body)

    # ---------------------------------------------------------------------------------- read

    @mcp.tool(annotations=READ)
    async def get_overview(ctx: Context) -> Any:
        """Everything at a glance: fleet totals (hashrate in H/s, power, efficiency), the odds of finding a block, network state, active alerts,
        recent events and any blocks found. Call this first."""
        return await api(ctx, "GET", "/api/v1/overview")

    @mcp.tool(annotations=READ)
    async def list_miners(ctx: Context, status: str | None = None, tag: str | None = None, search: str | None = None) -> Any:
        """List monitored miners with live readings. Filter by status (online, degraded, offline, paused), tag, or a search string."""
        return await api(ctx, "GET", "/api/v1/devices", params={"status": status, "tag": tag, "q": search})

    @mcp.tool(annotations=READ)
    async def get_miner(ctx: Context, miner_id: str) -> Any:
        """One miner in full detail (all readings, pools, capabilities). miner_id comes from list_miners."""
        return await api(ctx, "GET", f"/api/v1/devices/{miner_id}")

    @mcp.tool(annotations=READ)
    async def get_history(ctx: Context, range: str = "24h", metrics: str = "hashrate_hs,power_w", miner_id: str | None = None) -> Any:
        """Time series. range like 6h, 24h, 7d, 30d. metrics comma separated from: online, hashrate_hs, power_w, efficiency_j_th, temp_asic_c, temp_vr_c,
        fan_pct, fan_rpm, frequency_mhz, shares_accepted, shares_rejected, best_diff, uptime_s (add :max for peaks). Omit miner_id for the fleet."""
        if miner_id:
            return await api(ctx, "GET", f"/api/v1/devices/{miner_id}/history", params={"range": range, "metrics": metrics})
        return await api(ctx, "GET", "/api/v1/fleet/history", params={"range": range, "metrics": metrics})

    @mcp.tool(annotations=READ)
    async def get_odds(ctx: Context, hashrate_ths: float | None = None, difficulty: float | None = None, power_w: float | None = None,
                       growth: float | None = None) -> Any:
        """The user's chance of finding a block (per day/month/year...), expected wait, electricity cost versus expected value, and plain-English sentences
        to quote. Pass hashrate_ths (TH/s), difficulty, power_w or growth (0.3 = difficulty +30%/yr) for a what-if."""
        return await api(ctx, "GET", "/api/v1/odds", params={"hashrate_ths": hashrate_ths, "difficulty": difficulty, "power_w": power_w, "growth": growth})

    @mcp.tool(annotations=READ)
    async def get_network(ctx: Context) -> Any:
        """Bitcoin network state: block height, difficulty, network hashrate, halving and difficulty-adjustment countdowns, fees, BTC price, and which source answered."""
        return await api(ctx, "GET", "/api/v1/network")

    @mcp.tool(annotations=READ)
    async def get_node_and_pool(ctx: Context) -> Any:
        """The user's Bitcoin node (sync, peers, version) and pool statistics (workers, best shares), if configured."""
        node = await api(ctx, "GET", "/api/v1/node")
        pool = await api(ctx, "GET", "/api/v1/pool")
        return {"node": node, "pool": pool}

    @mcp.tool(annotations=READ)
    async def get_alerts(ctx: Context, include_rules: bool = False) -> Any:
        """Problems happening now (offline miners, overheating, hashrate drops...) and optionally the configured alert rules."""
        out = await api(ctx, "GET", "/api/v1/alerts/active")
        if include_rules:
            out["rules"] = (await api(ctx, "GET", "/api/v1/alerts/rules"))["rules"]
        return out

    @mcp.tool(annotations=READ)
    async def list_events(ctx: Context, limit: int = 30, type: str | None = None, miner_id: str | None = None) -> Any:
        """The activity log (restarts, new best shares, outages, difficulty changes, blocks). type filters, comma separated."""
        return await api(ctx, "GET", "/api/v1/events", params={"limit": limit, "type": type, "device_id": miner_id})

    @mcp.tool(annotations=READ)
    async def get_insights(ctx: Context) -> Any:
        """Plain-language observations and suggestions (weak WiFi, no node connected, no password, inefficient miner...). Good material for advice."""
        return await api(ctx, "GET", "/api/v1/insights")

    @mcp.tool(annotations=READ)
    async def get_diagnostics(ctx: Context) -> Any:
        """Self-check with pass/warn/fail results and fixes. Use it when something seems wrong or when helping file a bug report."""
        return await api(ctx, "GET", "/api/v1/system/diagnostics")

    @mcp.tool(annotations=READ)
    async def get_settings(ctx: Context) -> Any:
        """All settings (electricity price, polling, safety switches...). Contains no secrets."""
        return await api(ctx, "GET", "/api/v1/settings")

    # ---------------------------------------------------------------------------------- discover & add

    @mcp.tool(annotations=WRITE)
    async def scan_network(ctx: Context, cidrs: list[str] | None = None, wait_seconds: int = 60) -> Any:
        """Scan the local network for miners (Bitaxe, NerdQAxe, Avalon, Antminer...) and the user's Bitcoin node/pool. Waits until the scan finishes.
        cidrs like ['192.168.1.0/24'] (default: the server's own networks; inside Docker bridge mode pass the real LAN). Returns found miners and
        node/pool candidates plus a scan_id for add_discovered_miners."""
        job = await api(ctx, "POST", "/api/v1/discovery", body={"cidrs": cidrs})
        deadline = asyncio.get_running_loop().time() + max(5, min(wait_seconds, 180))
        while job["status"] == "running" and asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(1.5)
            job = await api(ctx, "GET", f"/api/v1/discovery/{job['id']}")
        job["scan_id"] = job["id"]
        return job

    @mcp.tool(annotations=WRITE)
    async def add_discovered_miners(ctx: Context, scan_id: str, hosts: list[str] | None = None, tags: list[str] | None = None) -> Any:
        """Start monitoring miners found by scan_network. hosts are 'ip:port' keys from the scan (default: all new ones). A miner that answers on
        two IP addresses is added once."""
        return await api(ctx, "POST", f"/api/v1/discovery/{scan_id}/adopt", body={"keys": hosts, "tags": tags or []})

    @mcp.tool(annotations=WRITE)
    async def add_miner(ctx: Context, host: str, name: str | None = None, tags: list[str] | None = None) -> Any:
        """Add one miner by IP address or host name (optionally host:port). The model is detected automatically."""
        return await api(ctx, "POST", "/api/v1/devices", body={"host": host, "name": name, "tags": tags or []})

    @mcp.tool(annotations=WRITE)
    async def update_miner(ctx: Context, miner_id: str, name: str | None = None, tags: list[str] | None = None, enabled: bool | None = None,
                           notes: str | None = None, power_override_w: float | None = None) -> Any:
        """Rename, tag, annotate, enable/disable a miner. power_override_w sets watts for miners that don't report power (so efficiency can be shown)."""
        body = {k: v for k, v in {"name": name, "tags": tags, "enabled": enabled, "notes": notes, "power_override_w": power_override_w}.items() if v is not None}
        return await api(ctx, "PATCH", f"/api/v1/devices/{miner_id}", body=body)

    @mcp.tool(annotations=DESTRUCTIVE)
    async def remove_miner(ctx: Context, miner_id: str, keep_history: bool = False) -> Any:
        """Stop monitoring a miner (does not touch the miner itself). Deletes its history unless keep_history is true. Confirm with the user first."""
        return await api(ctx, "DELETE", f"/api/v1/devices/{miner_id}", params={"keep_history": keep_history})

    # ---------------------------------------------------------------------------------- control

    @mcp.tool(annotations=DESTRUCTIVE)
    async def restart_miner(ctx: Context, miner_id: str) -> Any:
        """Reboot a miner. Hashing stops for about a minute. Ask the user before restarting a miner that is hashing well."""
        return await api(ctx, "POST", f"/api/v1/devices/{miner_id}/actions/restart", body={})

    @mcp.tool(annotations=WRITE)
    async def identify_miner(ctx: Context, miner_id: str) -> Any:
        """Make a miner flash its screen/LED so the user can find it physically."""
        return await api(ctx, "POST", f"/api/v1/devices/{miner_id}/actions/identify", body={})

    @mcp.tool(annotations=DESTRUCTIVE)
    async def run_miner_action(ctx: Context, miner_id: str, action: str, params: dict[str, Any] | None = None, dry_run: bool = False) -> Any:
        """Run a control action. action: restart | identify | pause | resume | set_pool {url, port, user, password?, role: primary|fallback} |
        set_fan {auto?, speed_pct?, temp_target_c?} | set_tuning {frequency_mhz?, core_voltage_mv?} (tuning is off unless the user enabled it in Settings > Safety;
        values must be ones the miner lists). Use dry_run=true to validate first. Everything is audited."""
        return await api(ctx, "POST", f"/api/v1/devices/{miner_id}/actions/{action}", body={"params": params or {}, "dry_run": dry_run})

    @mcp.tool(annotations=DESTRUCTIVE)
    async def run_bulk_action(ctx: Context, action: str, params: dict[str, Any] | None = None, miner_ids: list[str] | None = None,
                              tag: str | None = None, all_miners: bool = False, dry_run: bool = True) -> Any:
        """Apply one action to many miners, for example moving every miner to the user's own pool (set_pool). Defaults to a PREVIEW (dry_run=true):
        show the user the result, and only send dry_run=false after they agree."""
        return await api(ctx, "POST", "/api/v1/devices/actions",
                         body={"action": action, "params": params or {}, "device_ids": miner_ids, "tag": tag, "all": all_miners, "dry_run": dry_run})

    # ---------------------------------------------------------------------------------- configure

    @mcp.tool(annotations=WRITE)
    async def configure_source(ctx: Context, kind: str, url: str, name: str | None = None, rpc_user: str | None = None,
                               rpc_password: str | None = None, test_only: bool = False) -> Any:
        """Connect the user's Bitcoin node or pool. kind: bitcoin_core (needs rpc_user + rpc_password, ask the user), public_pool (Umbrel/Start9, use the
        API port e.g. http://umbrel.local:2019), ckpool (https://solo.ckpool.org), mempool_space. The connection is tested first; test_only=true only tests."""
        secret = {k: v for k, v in {"rpc_user": rpc_user, "rpc_password": rpc_password}.items() if v}
        body = {"kind": kind, "url": url, "name": name, "secret": secret}
        if test_only:
            return await api(ctx, "POST", "/api/v1/sources/test", body=body)
        return await api(ctx, "POST", "/api/v1/sources", body=body)

    @mcp.tool(annotations=READ)
    async def list_notification_channel_types(ctx: Context) -> Any:
        """Which notification services are supported (ntfy, Telegram, Discord, Slack, webhook, email, Pushover...) and exactly which fields each needs."""
        return await api(ctx, "GET", "/api/v1/notifications/channel-types")

    @mcp.tool(annotations=WRITE)
    async def create_notification_channel(ctx: Context, kind: str, name: str, config: dict[str, Any] | None = None, secret: dict[str, str] | None = None,
                                          send_test: bool = True) -> Any:
        """Add a place alerts are sent. Use list_notification_channel_types for the fields; secret fields (tokens, webhook URLs) go in `secret`.
        Sends a test message by default so the user can confirm it arrived."""
        created = await api(ctx, "POST", "/api/v1/notifications/channels", body={"kind": kind, "name": name, "config": config or {}, "secret": secret or {}})
        if send_test:
            created["test"] = await api(ctx, "POST", f"/api/v1/notifications/channels/{created['channel']['id']}/test")
        return created

    @mcp.tool(annotations=WRITE)
    async def update_settings(ctx: Context, patch: dict[str, Any]) -> Any:
        """Change settings with a partial object, e.g. {"energy": {"price_per_kwh": 0.09}}, {"units": {"temperature": "f"}},
        {"mining": {"addresses": ["bc1q..."]}}, {"safety": {"allow_tuning": true}}. Ask before changing safety switches."""
        return await api(ctx, "PATCH", "/api/v1/settings", body=patch)

    @mcp.tool(annotations=WRITE)
    async def create_alert_rule(ctx: Context, kind: str, name: str | None = None, params: dict[str, Any] | None = None, severity: str | None = None,
                                channel_ids: list[str] | None = None) -> Any:
        """Create an alert rule. Kinds and their parameters: GET /api/v1/alerts/rule-types (device_offline, temp_high, hashrate_drop, reject_rate_high, ...)."""
        return await api(ctx, "POST", "/api/v1/alerts/rules",
                         body={"kind": kind, "name": name, "params": params or {}, "severity": severity, "channel_ids": channel_ids or []})

    @mcp.tool(annotations=WRITE)
    async def send_notification(ctx: Context, title: str, body: str = "", severity: str = "info") -> Any:
        """Send a message through the user's notification channels (severity: info, success, warning, critical)."""
        return await api(ctx, "POST", "/api/v1/notifications/send", params={"title": title, "body": body, "severity": severity})

    # ---------------------------------------------------------------------------------- resources & prompts

    @mcp.resource("bsmm://agent-guide", mime_type="application/json", description="Setup recipe, safety rules and common tasks for agents")
    def guide_resource() -> str:
        return json.dumps(agent_guide("http://<this-server>"), indent=2)

    @mcp.prompt(description="Walk a new user through setting up their mining monitor")
    def setup_my_miners() -> str:
        return (
            "Set up the Bitcoin Solo Miner Monitor for me. 1) call get_overview and tell me what is already configured. 2) call scan_network and show me "
            "the miners and node/pool candidates it found; add them with add_discovered_miners after I confirm. 3) If a node or pool was found, ask me for "
            "any credentials it needs and call configure_source. 4) Ask for my electricity price per kWh and apply it with update_settings. 5) Offer to set up "
            "phone alerts with create_notification_channel (ntfy is the easiest). 6) Finish with get_odds and explain my chances honestly and kindly."
        )

    @mcp.prompt(description="A friendly status report of the whole mining setup")
    def mining_report() -> str:
        return (
            "Give me a short mining status report: call get_overview, get_alerts and get_insights. Lead with anything that needs attention, then hashrate, "
            "power and efficiency, then my odds in plain English (be honest that solo mining is a lottery), then one or two helpful suggestions."
        )

    return mcp


class McpEntry:
    """ASGI app mounted at ``/mcp``: rejects unauthenticated calls early, then hands over to the MCP server."""

    def __init__(self, app: FastAPI, mcp_app: Any) -> None:
        self.app = app
        self.mcp_app = mcp_app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] == "http":
            ctx = self.app.state.ctx
            headers = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
            token = headers.get("authorization", "")[7:] if headers.get("authorization", "").lower().startswith("bearer ") else headers.get("x-api-key")
            principal = await ctx.auth.principal_from(bearer=token, session=None)
            if principal is None and ctx.settings.current.auth.mode != "none":
                body = json.dumps({"error": {"code": "auth_required", "message": "Send 'Authorization: Bearer <token>'.", "status": 401,
                                             "hint": "Create a token with `bsmm token create --scope control`."}}).encode()
                await send({"type": "http.response.start", "status": 401, "headers": [(b"content-type", b"application/json"), (b"www-authenticate", b"Bearer")]})
                await send({"type": "http.response.body", "body": body})
                return
            scope = {**scope, "path": "/", "raw_path": b"/", "root_path": ""}
        await self.mcp_app(scope, receive, send)


def build_http_app(app: FastAPI) -> Any:
    """Create the embedded MCP endpoint for ``app``. Returns the ASGI app to mount at /mcp."""
    server = build_server(AsgiBackend(app))
    mcp_app = server.streamable_http_app(
        streamable_http_path="/", json_response=True, stateless_http=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
    app.state.mcp_lifespan = mcp_app.router.lifespan_context
    app.state.mcp_asgi = mcp_app
    return McpEntry(app, mcp_app)
