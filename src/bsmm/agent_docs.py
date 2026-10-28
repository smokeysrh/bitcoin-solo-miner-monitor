"""Documentation written *for AI agents*: `llms.txt` and the machine-readable agent guide.

Kept in one place so the file in the repo root, the copy the server serves at `/llms.txt`, and the
JSON from `/api/v1/agent/guide` can never drift apart.
"""

from __future__ import annotations

from typing import Any

from bsmm import __version__

REPO = "https://github.com/smokeysrh/bitcoin-solo-miner-monitor"

SETUP_RECIPE: list[dict[str, Any]] = [
    {"step": 1, "goal": "Learn what this server is and how far setup has got",
     "request": {"method": "GET", "path": "/api/v1/meta"}, "notes": "No login needed. Look at auth.mode and setup.*"},
    {"step": 2, "goal": "Get a token (only if auth.mode is 'password')",
     "request": {"method": "POST", "path": "/api/v1/auth/tokens", "body": {"name": "my agent", "scope": "admin"}},
     "notes": "Needs an admin session or an existing admin token. On the server itself you can run: bsmm token create --name agent --scope admin"},
    {"step": 3, "goal": "Find the user's miners",
     "request": {"method": "POST", "path": "/api/v1/discovery", "body": {}},
     "notes": "Returns a job id. Poll GET /api/v1/discovery/{id} until status is 'finished' (about 20 s). Only private networks are scanned. "
              "If the server runs in Docker bridge mode pass the user's LAN, e.g. {\"cidrs\": [\"192.168.1.0/24\"]}."},
    {"step": 4, "goal": "Start monitoring what was found",
     "request": {"method": "POST", "path": "/api/v1/discovery/{id}/adopt", "body": {}},
     "notes": "Adds every new miner; a miner that answers on two IPs is added once. Add one by hand with POST /api/v1/devices {\"host\": \"192.168.1.50\"}."},
    {"step": 5, "goal": "Connect the user's Bitcoin node or solo pool (optional but recommended)",
     "request": {"method": "POST", "path": "/api/v1/sources", "body": {"kind": "public_pool", "url": "http://umbrel.local:2019"}},
     "notes": "The discovery result lists likely candidates under 'sources'. kinds: bitcoin_core (needs rpc_user/rpc_password in 'secret'), public_pool, ckpool, mempool_space. "
              "Ask the user for node credentials; never guess them."},
    {"step": 6, "goal": "Set the electricity price so costs are right",
     "request": {"method": "PATCH", "path": "/api/v1/settings", "body": {"energy": {"price_per_kwh": 0.12}}}, "notes": "Currency units are the user's local currency."},
    {"step": 7, "goal": "Set up an alert channel",
     "request": {"method": "POST", "path": "/api/v1/notifications/channels", "body": {"kind": "ntfy", "name": "Phone", "config": {"topic": "pick-a-secret-topic"}}},
     "notes": "GET /api/v1/notifications/channel-types lists every kind and its fields. Then POST /api/v1/notifications/channels/{id}/test."},
    {"step": 8, "goal": "Protect the dashboard (recommended if others share the network)",
     "request": {"method": "POST", "path": "/api/v1/auth/password", "body": {"new_password": "<ask the user>"}}, "notes": "Then create a token for yourself."},
    {"step": 9, "goal": "Verify",
     "request": {"method": "GET", "path": "/api/v1/overview"}, "notes": "One call with fleet totals, odds, network, alerts, events. Also GET /api/v1/system/diagnostics."},
]

#: The MCP tools, in the order the server registers them. tests/test_agent_docs.py fails if this drifts from the real server.
MCP_TOOLS: list[str] = [
    "get_overview", "list_miners", "get_miner", "get_history", "get_odds", "get_network", "get_node_and_pool", "get_alerts",
    "list_events", "get_insights", "get_diagnostics", "get_settings", "scan_network", "add_discovered_miners", "add_miner",
    "update_miner", "remove_miner", "restart_miner", "identify_miner", "run_miner_action", "run_bulk_action", "configure_source",
    "list_notification_channel_types", "create_notification_channel", "update_settings", "create_alert_rule", "send_notification",
]

TASKS: dict[str, str] = {
    "How are my miners doing?": "GET /api/v1/overview, then GET /api/v1/devices",
    "What are my odds of finding a block?": "GET /api/v1/odds (add ?hashrate_ths=50 for a what-if)",
    "What is my chance in the next 10 minutes?": "GET /api/v1/odds: horizons.ten_minutes (seconds=600), also in bsmm odds and MCP get_odds. "
        "This is a fixed-window Poisson chance of at least one block, not the chance of winning the very next network block. "
        "Bitcoin targets 10-minute blocks; the exact future block time is unknown. Past work never makes a miner due.",
    "Is anything wrong?": "GET /api/v1/alerts/active and GET /api/v1/insights",
    "Restart a miner": "POST /api/v1/devices/{id}/actions/restart (needs 'control' scope)",
    "Point miners at my own pool/node": "POST /api/v1/devices/actions {\"action\":\"set_pool\",\"all\":true,\"params\":{...}} previews by default; send dry_run=false to apply",
    "History / charts": "GET /api/v1/fleet/history?range=24h&metrics=hashrate_hs,power_w",
    "Live updates": "GET /api/v1/stream?topics=device,event,fleet (Server-Sent Events)",
    "Prometheus / Grafana": "GET /metrics",
    "Report a bug": "Attach the output of GET /api/v1/system/diagnostics to a GitHub issue",
}

SAFETY: list[str] = [
    "Control actions are audited and can be switched off in Settings > Safety (allow_control). Frequency/voltage changes are OFF until the user enables allow_tuning.",
    "Bulk actions preview by default (dry_run: true). Show the user the preview before sending dry_run=false.",
    "Secrets (RPC passwords, bot tokens, webhook URLs) are write-only: they are never returned by any endpoint.",
    "Do not guess node credentials, wallet addresses or passwords. Ask the user.",
    "Network scans are limited to private address ranges.",
    "Restarting a miner interrupts hashing for about a minute. Solo mining odds are not affected by short outages.",
]


def agent_guide(base: str, *, auth_mode: str = "none", demo: bool = False) -> dict[str, Any]:
    return {
        "name": "Bitcoin Solo Miner Monitor",
        "version": __version__,
        "summary": "Dashboard and API for solo Bitcoin miners: discovers miners, monitors them, watches the user's node and pool, "
                   "computes block odds, alerts, and lets you control miners within safe limits.",
        "base_url": base,
        "api_base": f"{base}/api/v1",
        "demo": demo,
        "auth": {
            "mode": auth_mode,
            "how": "Send 'Authorization: Bearer <token>' (or header X-API-Key). When mode is 'none' no credentials are needed.",
            "scopes": {"read": "look only", "control": "restart / scan / add miners / change pools", "admin": "settings, sources, channels, rules, tokens"},
            "create_token_on_server": "bsmm token create --name agent --scope admin",
        },
        "setup_recipe": SETUP_RECIPE,
        "common_tasks": TASKS,
        "safety": SAFETY,
        "errors": 'Every error is {"error": {"code", "message", "hint", "status"}}. Switch on code; show message to the user; follow hint.',
        "units": {"hashrate": "H/s (fields end in _hs)", "power": "watts (_w)", "temperature": "Celsius (_c)", "efficiency": "J/TH (_j_th)",
                  "difficulty": "plain number", "time": "Unix seconds"},
        "mcp": {
            "streamable_http": f"{base}/mcp",
            "stdio": f"bsmm mcp --url {base} --token <token>",
            "tools": MCP_TOOLS,
        },
        "links": {"openapi": f"{base}/openapi.json", "interactive_docs": f"{base}/docs", "llms_txt": f"{base}/llms.txt", "source": REPO,
                  "issues": f"{REPO}/issues"},
    }


def llms_txt(base: str = "http://localhost:8420") -> str:
    g = agent_guide(base)
    recipe = "\n".join(
        f"{s['step']}. {s['goal']}: `{s['request']['method']} {s['request']['path']}`"
        + (f" with body `{_j(s['request']['body'])}`" if "body" in s["request"] else "")
        + (f"\n   {s['notes']}" if s.get("notes") else "")
        for s in SETUP_RECIPE
    )
    tasks = "\n".join(f"- {k} -> {v}" for k, v in TASKS.items())
    safety = "\n".join(f"- {s}" for s in SAFETY)
    return f"""# Bitcoin Solo Miner Monitor

> Self-hosted dashboard, REST API and MCP server for people who solo mine Bitcoin with ASIC miners (Bitaxe, NerdQAxe, Lucky/Magic Miner, Avalon Nano/Q, Antminer and other cgminer-API miners). It discovers miners on the LAN, monitors hashrate, temperature, power and shares, connects to the user's own Bitcoin node and solo pool (Public Pool, ckpool), computes the odds of finding a block, sends alerts, and lets an agent control miners within safe limits. Version {__version__}.

This server: {base}
Everything below is also available as JSON at {base}/api/v1/agent/guide.

## Set it up for a user (about two minutes)

{recipe}

## Authentication

- Read {base}/api/v1/meta first (no login). If `auth.mode` is `none`, no credentials are needed.
- Otherwise send `Authorization: Bearer <token>`. Scopes: `read` < `control` < `admin`.
- On the machine running the app: `bsmm token create --name agent --scope admin` prints a token once.

## Common tasks

{tasks}

## Safety rules for agents

{safety}

## Conventions

- Field names carry units: `hashrate_hs` (H/s), `power_w`, `temp_asic_c`, `efficiency_j_th`.
- Errors are always `{{"error": {{"code", "message", "hint", "status"}}}}`.
- Bulk and destructive operations take `dry_run`.
- Live updates: `GET {base}/api/v1/stream?topics=device,fleet,event` (Server-Sent Events).

## Docs

- [OpenAPI schema]({base}/openapi.json): every endpoint with descriptions and examples
- [Interactive API docs]({base}/docs)
- [MCP server]({base}/mcp): streamable HTTP; or run `bsmm mcp --url {base} --token <token>` for stdio
- [Source and issues]({REPO}): attach `GET {base}/api/v1/system/diagnostics` to bug reports

## Optional

- [Prometheus metrics]({base}/metrics)
- [Agent guide as JSON]({base}/api/v1/agent/guide) ({len(g['setup_recipe'])} setup steps)
"""


def _j(obj: Any) -> str:
    import json

    return json.dumps(obj, separators=(",", ":"))
