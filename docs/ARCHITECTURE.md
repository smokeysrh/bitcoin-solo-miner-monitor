# Architecture

One Python process serves a REST API, an MCP endpoint, a live event stream and the built web UI. State is one SQLite file plus one key file. There is no external service to run.

```
 miners ──(HTTP / cgminer TCP)──► drivers ─┐
 node / pool / mempool.space ──► sources ──┤
                                           ▼
                          engine: Fleet (poll) · Network · Alerts · Insights · Odds
                                           │            │
                              storage (SQLite, rollups)  EventBus ──► SSE ──► web UI
                                           │            │
                                        REST API ◄──────┴──► MCP tools, CLI
```

## Backend (`src/bsmm`)

| Package | Job |
| --- | --- |
| `drivers/` | One class per protocol family. `axeos.py` talks to Bitaxe/NerdQAxe-style HTTP APIs, `cgminer.py` to the cgminer TCP API (Avalon, Antminer, Braiins). `registry.py` fingerprints a host and picks a driver; `catalog.py` names models and ASIC chips. Drivers return a normalised `Telemetry`, so nothing above them knows which brand it is talking to. |
| `engine/fleet.py` | Polls every device concurrently, backs off failing ones, keeps live state, and is the **only** path for control actions (`run_action`: permission check, safety settings, audit log). |
| `engine/alerts.py` | Rules evaluated on every poll. State rules (offline, hot...) need to hold for a while, fire once, repeat after a cooldown and send "Resolved". Active alert state is persisted, so a restart doesn't forget one. |
| `engine/network.py`, `sources/` | Chain state from Bitcoin Core RPC, Public Pool, ckpool, mempool.space. Sources are interchangeable behind one interface; losing one degrades gracefully. |
| `engine/odds.py`, `mining.py` | Pure maths: block probability, expected time, economics, break-even. No I/O, fully unit-tested. |
| `engine/discovery.py` | Private-range scanner. Probes known ports, fingerprints, never writes. |
| `engine/insights.py` | Plain-language observations and setup nudges ("your node is 3 blocks behind", "no alert channel yet"). Rules, not a model. |
| `notify/` | Eight channel types behind one dispatcher; formatting per channel (Telegram HTML, Discord embeds...). A failed send is recorded, never swallowed. |
| `storage/` | `aiosqlite`, WAL mode. `samples.py` keeps raw samples 2 days, 1-minute rollups 90 days, hourly 2 years and daily forever, computed in SQL. `secrets.py` Fernet-encrypts credentials. |
| `api/` | FastAPI routes under `/api/v1`, security headers, SPA fallback. Errors are `{error: {code, message, hint, status}}`. |
| `mcp_server.py` | The same operations as MCP tools (27). `agent_docs.py` holds the agent guide; a test checks its tool list against the real server so it cannot drift. |
| `sim/`, `demo.py` | Simulators of real miners speaking the real protocols. Used by tests, `--demo`, and development, which is why nothing in the test suite ever touches hardware. |
| `cli/` | Typer CLI. Talks to a running server over the API (so it works the same on another machine), except `serve`, `demo` and `migrate-legacy`. |

### Design rules

- **Deterministic.** The app has no model calls. Anything decidable in code is decided in code.
- **Errors are not empty.** A failed read is an error with a hint, never an empty list.
- **Units in names.** `hashrate_hs`, `power_w`, `*_pct`, `*_s`.
- **Secrets are write-only.** Responses carry `has_password: true`, never the password.
- **One calculation, one place.** Number formatting in the UI lives in `web/src/lib/format.ts`; fleet performance is computed by the backend (`FleetSummary.performance_pct`) and displayed as-is.

## Frontend (`web`)

Vue 3 + TypeScript + Vite + Tailwind v4, Pinia for state, reka-ui for accessible primitives, ECharts (lazy-loaded chunk) for charts, vue-draggable-plus for the dashboard editor. The build lands in `src/bsmm/web` and is shipped inside the Python wheel.

- `lib/` holds framework-free code (API client, SSE stream with reconnect and watchdog, formatting, theme, fuzzy search, CSV, glossary).
- `stores/` mirror server state; the SSE stream patches them live and refetches after a reconnect.
- `components/dashboard/registry.ts` declares the 16 widgets (id, title, allowed spans). The layout is saved in the `ui.dashboard` setting, so it follows the user to any browser.
- Theme tokens (`bg-surface-1`, `text-muted`, `text-accent-text`) are CSS variables per theme (dark, black, light); every text colour is checked at 4.5:1 with axe in all three.
- `public/sw.js` makes it installable; it never caches API responses.

## Tests

- `pytest`: ~800 backend tests (drivers against recorded replies, simulators end to end, alert rules, storage, API, MCP, CLI).
- `vitest`: formatting and pure UI logic.
- Playwright: browser flows on desktop and phone, plus an axe audit script (`web/e2e/audit.mjs`).
- Live checks against real hardware are opt-in (`BSMM_LIVE=1`) and read-only.
