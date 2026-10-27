# Bitcoin Solo Miner Monitor

**One dashboard for every solo miner you own.** It finds your miners, shows how they're doing, tells you your real odds of finding a block, and pings your phone when something breaks. It runs on your own computer. Nothing is sent anywhere, and there are no accounts.

Works with miners that solo-mine to **your own node**, to a **public solo pool** (Public Pool, ckpool, solo.ckpool.org and friends) or to a **shared node**.

![Dashboard](docs/screenshots/dashboard.png)

## Try it in 30 seconds

No miners? No problem. The demo runs a simulated fleet and saves nothing.

```bash
pipx install bitcoin-solo-miner-monitor
bsmm demo
```

Open <http://localhost:8420>. Or with Docker: `docker run --rm -p 8420:8420 ghcr.io/smokeysrh/bitcoin-solo-miner-monitor serve --demo`.

## Install for real

| You have | Do this |
| --- | --- |
| A NAS, Raspberry Pi, home server | `docker compose up -d` using [`docker-compose.yml`](docker-compose.yml) |
| Windows, macOS, Linux desktop | `pipx install bitcoin-solo-miner-monitor`, then `bsmm setup` |
| Umbrel | Template in [`packaging/umbrel/`](packaging/umbrel) (untested, see below) |

Open `http://<that computer>:8420`. The setup wizard scans your network, adopts the miners it finds, connects your node or pool and asks what you pay for electricity. Everything it asks can also be done later in Settings.

Details, environment variables and autostart are in [`docs/PACKAGING.md`](docs/PACKAGING.md). Python 3.11+.

> There is no one-click Windows installer in 1.0. The old 0.9 installer is gone on purpose. Use `pipx` or Docker Desktop.

## What you get

**Fleet**
- Automatic discovery (and add-by-address), with model and firmware recognised.
- Live hashrate, power, temperature, fan, shares, best share, pool, uptime, per miner and for the fleet. Updates stream in without refreshing.
- Safe controls: restart, identify, pause/resume, change pool, fan and (opt-in) frequency/voltage. Bulk actions preview first. Every action is audited.
- Per-miner pages with history, pool settings, logs and an events timeline.
- History is kept in compact rollups, so a year of data stays small.

**Your node and pools**
- Sources: Bitcoin Core (RPC), Public Pool, ckpool, mempool.space.
- Block height, sync state, mempool, fee estimates, recent blocks, difficulty-adjustment countdown.

**Odds and money**
- Chance of finding a block per day, month and year, in plain English and without hype. Solo mining is a lottery and the app says so.
- Electricity cost, efficiency (J/TH), break-even and "cost per lottery ticket" with your own tariff.

**Alerts**
- 15 ready-made rules: offline, hot, fan stopped, hashrate drop, fleet drop, high reject rate, pool fallback, node down or behind, new best share, **block found**, restarts, difficulty change, firmware change and more.
- 8 channels: Discord, Telegram, ntfy, Slack, Pushover, email, generic webhook, and Apprise (which reaches nearly everything else).
- Quiet hours (mutes info and success only, never a critical alert), cooldowns, "Resolved" messages, and a Test button on every channel.

**UI that fits you**
- Customizable dashboard: 16 widgets you drag, hide and resize. Layout is saved.
- Dark, black (OLED) and light themes, accent colours, density, units, 12/24 hour.
- Command palette (`Ctrl/Cmd+K`), keyboard shortcuts, installable as an app (PWA), phone layout, and a wall-display **Kiosk** mode at `/kiosk`.
- Jargon is explained in place. Accessibility is checked in all three themes with axe.

![Miner page](docs/screenshots/miner.png)

| Odds | Miners table | Phone |
| --- | --- | --- |
| ![Odds](docs/screenshots/odds.png) | ![Miners](docs/screenshots/miners-table.png) | ![Phone](docs/screenshots/phone.png) |

## Built for AI agents too

Point your agent at the app and it can set everything up for the user.

- **`GET /llms.txt`**: a step-by-step setup recipe and the safety rules. Same text from `bsmm agent-guide`.
- **MCP server** (27 tools) at `POST /mcp`, or `bsmm mcp --url ... --token ...` for stdio clients.
- **REST API** with a full OpenAPI schema at `/openapi.json` and `/docs`. Errors carry a `hint` that says what to do next.
- **Scoped tokens**: `read`, `control`, `admin` (`bsmm token create --name agent --scope read`).
- **CLI that works unattended**: `bsmm setup --yes ...`, `bsmm status --json`, `bsmm doctor`.
- A [`skills/solo-miner-monitor`](skills/solo-miner-monitor/SKILL.md) skill and [`AGENTS.md`](AGENTS.md).

Agents are told to ask before touching a miner, never to guess credentials or payout addresses, and not to tell anyone they're "due" a block.

## Hardware, honestly

| Family | Status |
| --- | --- |
| NerdQAxe++, Magic Miner BG02 | Tested on real hardware (read-only) |
| Bitaxe (Ultra, Supra, Gamma, GT), other AxeOS devices | Driver + simulator + fixtures |
| Avalon Nano 3 and other cgminer-API devices | Driver + simulator + fixtures |
| Antminer, Braiins OS | Driver + simulator + fixtures |

Tested on real hardware means I ran it against actual miners. The rest follow the same documented APIs and are covered by recorded replies, but I haven't owned every one. If yours misbehaves, run `bsmm doctor` and open an issue; adding a model is a small change (see [`AGENTS.md`](AGENTS.md)).

The Umbrel template and the GitHub release workflow have not been run yet.

## Safety

- Never writes to a miner unless you (or a token with `control`) ask, and tuning stays off until you switch it on.
- Passwords, RPC logins, bot tokens and webhook URLs are stored encrypted and are write-only: no endpoint returns them.
- Network scans stay inside private ranges.
- Details and how to report a problem: [`SECURITY.md`](SECURITY.md).

## Coming from 0.9?

```bash
bsmm migrate-legacy path/to/old/data/config.db
```

Your miners are imported and the old database is left untouched. The rewrite changed the app completely; see the [CHANGELOG](CHANGELOG.md) and [`docs/AUDIT.md`](docs/AUDIT.md).

## Docs

[`docs/PACKAGING.md`](docs/PACKAGING.md) install and release · [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) how it's built · [`AGENTS.md`](AGENTS.md) for agents · [`CONTRIBUTING.md`](CONTRIBUTING.md) · [`SECURITY.md`](SECURITY.md)

## License

MIT. See [LICENSE](LICENSE).
