---
name: solo-miner-monitor
description: Set up, check on and operate Bitcoin Solo Miner Monitor, the self-hosted dashboard for people who solo mine with Bitaxe, NerdQAxe, Avalon, Antminer and similar miners. Use when the user asks about their miners' health, hashrate, temperatures, odds of finding a block, their node or solo pool, alerts, or wants the monitor installed and configured.
---

# Solo Miner Monitor

A self-hosted app with a web UI, REST API, MCP server and CLI. It finds miners on the local network, watches them, connects to the user's Bitcoin node / solo pool, computes the real odds of finding a block, sends alerts and can restart or reconfigure miners within safe limits.

The server explains itself. **Fetch `<server>/llms.txt` first** (default `http://<host>:8420/llms.txt`) and follow it; this skill only tells you how to behave.

## Decide what the user needs

| The user says | Do this |
| --- | --- |
| "How are my miners?" / "Is anything wrong?" | `GET /api/v1/overview` and `GET /api/v1/insights`. Summarise in two or three sentences, problems first. |
| "What are my odds?" | `GET /api/v1/odds`. Quote `plain_english`. Never imply they are "close" or "due". |
| "Set it up" / "install it" | Setup flow below. |
| "Restart / pause X" | Confirm with the user, then `POST /api/v1/devices/{id}/actions/restart` (`control` scope). |
| "Change my pool / address" | Read the new address back to the user, preview with `dry_run: true`, apply only after they confirm. |
| "Make it faster" | Tuning is off by default. Explain the heat/power trade-off and ask them to enable it themselves in Settings > Safety. |

## Setup flow

1. Find the server: try `http://localhost:8420/api/v1/meta`, the user's hostname, or ask. `bsmm doctor` helps on the host itself.
2. Not installed? Pick the user's own situation: Docker (best on NAS/Umbrel-style hosts, use the project's image and pass the LAN range), or `pipx install` of the release package on a normal computer. Start it with `bsmm start` (or `docker compose up -d`). Try it without any hardware: `bsmm demo`.
3. `GET /api/v1/meta` (no login). Note `auth.mode` and `setup.*`.
4. Scan and adopt: `POST /api/v1/discovery`, poll `GET /api/v1/discovery/{id}` until `finished`, then `POST /api/v1/discovery/{id}/adopt`. Show the user what was found before adopting.
5. Connect their node or pool (`POST /api/v1/sources`). Discovery lists candidates. **Ask for node RPC credentials; never guess them.**
6. Electricity price (`PATCH /api/v1/settings` `{"energy": {"price_per_kwh": ...}}`): ask for the number on their bill.
7. Alerts: ntfy is quickest (`POST /api/v1/notifications/channels`, then `/test`). Tell the user to install the ntfy app and subscribe to the topic.
8. Password: recommend one if anyone else shares the network (`POST /api/v1/auth/password`), then create yourself a scoped token.
9. Verify with `GET /api/v1/overview` and `GET /api/v1/system/diagnostics`; report what you did and anything left for the user.

## Rules

- Be honest and plain. Solo mining is a lottery; most users will never find a block. Say so kindly if asked.
- Ask before touching a miner. Every control action is logged and interrupts hashing for about a minute.
- Prefer the least power that does the job: a `read` token to look, `control` to act, `admin` only for setup.
- Never print or store tokens, RPC passwords, bot tokens or webhook URLs in chat history. Secrets are write-only in the API.
- Report errors with the server's `hint`; it says what to do next.
- Units are in the field names: `hashrate_hs` is hashes per second, `efficiency_j_th` is joules per terahash (lower is better).

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
