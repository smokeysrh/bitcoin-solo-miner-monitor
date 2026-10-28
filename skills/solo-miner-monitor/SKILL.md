---
name: solo-miner-monitor
description: Set up, check on and operate Bitcoin Solo Miner Monitor, the self-hosted dashboard for people who solo mine with Bitaxe, NerdQAxe, Avalon, Antminer and similar miners. Use when the user asks about their miners' health, hashrate, temperatures, odds of finding a block, their node or solo pool, alerts, or wants the monitor installed and configured.
---

# Solo Miner Monitor

A self-hosted app with a web UI, REST API, MCP server and CLI. It finds compatible AxeOS and cgminer-API miners on the local network, watches them, connects to the user's Bitcoin node / solo pool, estimates block odds, sends alerts and can restart or reconfigure miners within safe limits. Readings and controls depend on firmware and protocol support.

The server explains itself. **Fetch `<server>/llms.txt` first** (default `http://<host>:8420/llms.txt`) and follow it; this skill only tells you how to behave.

## Decide what the user needs

| The user says | Do this |
| --- | --- |
| "How are my miners?" / "Is anything wrong?" | `GET /api/v1/overview` and `GET /api/v1/insights`. Summarise in two or three sentences, problems first. |
| "What are my odds?" | `GET /api/v1/odds`. Quote `plain_english`. Never imply they are "close" or "due". |
| "Set it up" / "install it" | Setup flow below. |
| "Restart / pause X" | Confirm the action and target, then use the matching `/actions/restart` or `/actions/pause` endpoint (`control` scope). |
| "Change my pool / address" | Read the new address back to the user, preview with `dry_run: true`, apply only after they confirm. |
| "Make it faster" | Tuning is off by default. Explain the heat/power trade-off and ask them to enable it themselves in Settings > Safety. |

## Setup flow

1. Find the server: try `http://localhost:8420/api/v1/meta`, the user's hostname, or ask. `bsmm doctor` helps on the host itself.
2. Not installed? Read the [repository's AGENTS.md](../../AGENTS.md) and choose the official platform artifact from the [latest stable release](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/latest): Windows installer, Python wheel, or GHCR image for Docker. Use the wheel URL from that release with pipx, rather than a bare package name on PyPI. Follow [PACKAGING.md](../../docs/PACKAGING.md). Back up existing app data and its encryption key before upgrades; preserve the data directory or Docker volume and miner configuration. Start through the chosen launcher, `bsmm start`, or `docker compose up -d`. Try it without hardware: `bsmm demo`.
3. Read the running app's `/llms.txt` or `/api/v1/agent/guide`, then `GET /api/v1/meta` (no login). Note `auth.mode` and `setup.*`. Set authentication for the network before sharing access, and use the least scope needed. Setup may need admin access temporarily; routine monitoring uses `read`.
4. Scan the user's private range with `POST /api/v1/discovery`, then poll `GET /api/v1/discovery/{id}` until `finished`. Show the miner and node/pool candidates and wait for confirmation before adoption. Use `POST /api/v1/discovery/{id}/adopt` with `keys` containing only approved `host:port` values; an empty body adopts every new non-duplicate miner.
5. Connect the approved node or pool (`POST /api/v1/sources`). Ask for missing RPC credentials only; let the user enter them through secure app fields. Never guess credentials or copy them into chat.
6. Electricity price (`PATCH /api/v1/settings` `{"energy": {"price_per_kwh": ...}}`): preserve an existing tariff; ask for the number on their bill if missing.
7. Alerts: preserve existing channels or ask which destination the user wants. `GET /api/v1/notifications/channel-types` lists choices. Configure the chosen channel, then send an agreed test.
8. Start with monitoring only. Use a read-scoped token after setup, and keep any admin token in a protected local store. For a legacy v0.9.x installation, preserve its data and follow PACKAGING.md's miner-configuration import instructions; historical telemetry stays in the legacy archive.
9. Verify the dashboard, `GET /api/v1/health`, `GET /api/v1/overview` and `GET /api/v1/system/diagnostics`. Return the dashboard URL and a plain-English report of health, hashrate, alerts and odds. Report anything still unavailable.

### Unattended setup needs prior approval

`bsmm discover --cidr 192.168.1.0/24 --json` scans without adopting; use the user's actual private range. Review the result with them before acting. `bsmm setup --yes` scans again, skips confirmation, can adopt all new miners and connect a discovered Public Pool, and skips the password prompt. Use it only when that behavior and range are approved and authentication is arranged. If approval names specific devices, use the API adoption flow for that scan instead. Setup output may include a new admin token; keep it out of chat and logs.

## Rules

- Be honest and plain. Solo mining is a lottery; most users will never find a block. Say so kindly if asked.
- Ask before restarting a miner, changing pools or payout addresses, tuning, changing firmware, deleting data or other destructive actions. Read payout changes back through a private confirmation view. Controls are audited; downtime depends on the action and firmware, and lost hashing time reduces the chance of finding a block.
- Prefer the least power that does the job: a `read` token to look, `control` to act, `admin` only for setup.
- Never print or store tokens, RPC passwords, bot tokens or webhook URLs in chat history. Secrets are write-only in the API.
- Report errors with the server's `hint`; it says what to do next.
- Units are in the field names: `hashrate_hs` is hashes per second, `efficiency_j_th` is joules per terahash (lower is better).
- When available, `horizons.ten_minutes` is the **Next 10 minutes** estimate: chance across a fixed 600-second window. The next network block can arrive at any time. Never promise a block or profit.

## Quick reference

```bash
bsmm status --json          # fleet summary
bsmm list --json            # miners
bsmm odds                   # your chances, in words
bsmm doctor                 # why isn't it working
bsmm token create --name agent --scope read
bsmm mcp --url http://HOST:8420 --token TOKEN   # MCP over stdio
```

MCP tools (27; the server lists them with descriptions): reading `get_overview`, `list_miners`, `get_miner`, `get_history`, `get_odds`, `get_network`, `get_node_and_pool`, `get_alerts`, `list_events`, `get_insights`, `get_diagnostics`, `get_settings`; acting `scan_network`, `add_discovered_miners`, `add_miner`, `update_miner`, `remove_miner`, `restart_miner`, `identify_miner`, `run_miner_action`, `run_bulk_action`, `configure_source`, `create_notification_channel`, `update_settings`, `create_alert_rule`, `send_notification`.
