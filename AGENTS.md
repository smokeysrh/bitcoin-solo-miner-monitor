# AGENTS.md

Two kinds of agent read this file. Jump to the part that is yours.

- **Part 1: you are helping a person run Solo Miner Monitor** (set it up, check on their miners, answer "what are my odds").
- **Part 2: you are changing this repository** (fixing a bug, adding a driver, improving the UI).

---

## Part 1: operating the app for a user

Everything you need is served by the app itself, so you never have to guess endpoints:

| What | Where |
| --- | --- |
| Step-by-step setup recipe and safety rules | `GET /llms.txt` (text) or `GET /api/v1/agent/guide` (JSON) |
| Every endpoint, with examples | `GET /openapi.json`, browsable at `/docs` |
| MCP server (tools for Claude, Cursor, Hermes...) | `POST /mcp` (streamable HTTP) or `bsmm mcp --url <url> --token <token>` (stdio) |
| Health and "why isn't it working" | `GET /api/v1/system/diagnostics` or `bsmm doctor` |
| Plain-language observations | `GET /api/v1/insights` |

The default address is `http://<host>:8420`. `GET /api/v1/meta` needs no login and tells you the version, whether a password is set and how far setup has got.

### The shortest useful path

1. `GET /api/v1/meta`. If `auth.mode` is `password`, ask the user for a token (`bsmm token create --name agent --scope read`).
2. `GET /api/v1/overview` answers "how are my miners doing?" in one call (fleet totals, odds, network, alerts, recent events).
3. Setting up from nothing: follow the nine steps in `/llms.txt`. In short: scan (`POST /api/v1/discovery`), adopt, connect the node/pool, set the electricity price, add an alert channel, set a password.

### Rules you must follow

- **Ask before you change anything on a miner.** Restart, pause and pool changes interrupt hashing and are audited. Bulk actions preview by default (`dry_run: true`): show the user the preview first.
- **Never guess credentials**, node RPC logins, payout addresses or passwords. If you need one, ask.
- **A wrong payout address loses a found block.** When changing a miner's pool, read the address back to the user.
- Frequency/voltage ("tuning") is off until the user enables `safety.allow_tuning`. Do not turn it on for them.
- Read-only tokens are enough for monitoring. Use `control` only when the user asked for an action, and never `admin` unless you are doing setup.
- Honest odds: solo mining is a lottery. Do not tell users they are "close" or "due". The app's `plain_english` field is worded carefully; reuse it.
- Errors look like `{"error": {"code", "message", "hint", "status"}}`. The `hint` says what to do next.

### Units

Field names carry units: `hashrate_hs` (H/s), `power_w`, `temp_asic_c`, `efficiency_j_th`, `*_s` (seconds), `*_pct` (percent, 45 = 45%), `*_sat_vb`. Difficulty is a plain number. Fractions are 0..1 and say so (`progress`, `probability`).

---

## Part 2: working on this repository

### Layout

```
src/bsmm/            Python package (FastAPI app, drivers, engine, storage, CLI, MCP)
  drivers/           one file per protocol family; registry.py picks by fingerprint
  engine/            fleet polling, alerts, discovery, network state, odds
  sources/           Bitcoin Core RPC, Public Pool, ckpool, mempool.space
  sim/               simulators of real miners (used by tests, demo mode and development)
  api/               REST routes; mcp_server.py exposes the same operations as tools
  web/               built UI (generated; not committed)
web/                 Vue 3 + TypeScript + Tailwind v4 + Vite source of the UI
tests/               pytest (backend); web/src/**/*.test.ts (vitest); web/e2e (Playwright)
docs/                architecture, audit, packaging notes
```

### Commands

```bash
uv sync --extra dev                      # Python env in .venv (3.11+)
.venv/bin/python -m pytest               # backend tests (~800); live-hardware tests need BSMM_LIVE=1
.venv/bin/ruff check src tests           # lint
.venv/bin/mypy                           # strict types over src/

cd web && npm ci
npm run typecheck                        # vue-tsc
npm test                                 # vitest
npm run build                            # writes ../src/bsmm/web (served by the Python app)
npm run dev                              # UI dev server; BSMM_DEV_API=http://127.0.0.1:8421 to choose the backend

.venv/bin/bsmm serve --demo --port 8421  # simulated fleet, nothing saved: the safe thing to develop against
cd web && npx playwright test            # e2e against a running demo (BASE=http://localhost:6001 by default)
python scripts/gen_llms_txt.py           # regenerate llms.txt after touching src/bsmm/agent_docs.py
```

### Conventions that matter

- **Code over LLM.** Anything that can be decided deterministically is. The app has no model calls.
- **Never write to a real miner from a test.** Use the simulators in `src/bsmm/sim`. Live checks (`BSMM_LIVE=1`) are read-only.
- **An error and an empty result are different things.** Never collapse them (`except: return []` is a bug). Only "not found" may mean "no data".
- **One calculation, one implementation.** The UI formats numbers in `web/src/lib/format.ts`, mirroring `src/bsmm/units.py`. Do not add a second formatter.
- **Names carry units** and secrets are write-only: no endpoint returns an RPC password, bot token or webhook URL.
- **Every control action goes through `Fleet.run_action`**, which checks permissions, safety settings and writes the audit log.
- **Test the control.** A test that would still pass with the bug present proves nothing; make it fail first.
- Keyboard E2E tests must wait for the mounted UI before sending shortcuts: page load can finish before API bootstrap mounts `AppShell`. For the desktop palette, wait for `open-palette`, then use real key presses and assert input focus; do not replace shortcuts with clicks or sleeps.
- Keep user-facing text plain: short sentences, no jargon without a `<Term>` explanation (`web/src/lib/glossary.ts`).
- UI: semantic colour tokens only (`bg-surface-1`, `text-muted`, `text-accent-text`). Text must pass 4.5:1 in dark, black and light themes; run the axe audit (`web/e2e/audit.mjs`).
- Decorative overlays must preserve text contrast: the kiosk's accent glow is dark/black-only because it lowers light-theme subtle text below 4.5:1. The phone kiosk E2E covers this with axe.

### Adding support for a new miner

1. Capture its real replies (read-only): `bsmm capture <host> --out my-miner.json`. It shows what the app thinks the miner is and why, and removes Wi-Fi name, MAC, serial, pool users and addresses. Save a reviewed copy in `tests/fixtures/` (use the example payout address `bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq`). Identification rules are explained in `docs/miner-identification.md`.
2. Extend the nearest driver (`drivers/axeos.py` for AxeOS-like HTTP APIs, `drivers/cgminer.py` for the cgminer TCP API) or add one and register it in `drivers/registry.py`. Add the model to `drivers/catalog.py`.
3. Add or extend a simulator in `src/bsmm/sim` so the full path is testable.
4. Fingerprinting must be conservative: a wrong guess is worse than "unknown miner".

### Before you finish

`ruff check`, `mypy`, `pytest`, and for UI changes `npm run typecheck && npm test && npm run build`. If you changed the API, the OpenAPI schema and `llms.txt` update themselves; re-run `scripts/gen_llms_txt.py`.
