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
3. Setting up from nothing: use the [README setup prompt](README.md#let-your-agent-do-the-setup) and [platform install guide](docs/PACKAGING.md). Follow the running app's `/llms.txt` preflight and nine steps. Preserve data and the encryption key before an upgrade, arrange authentication before sharing access, scan the user's private range, show candidates and wait for confirmation before adopting. Preserve existing settings; ask only for missing credentials, tariff or alert choices.

`bsmm setup --yes` can adopt newly found miners and connect a discovered Public Pool without pausing. Get approval for that behavior and range first; it scans again. Use API adoption with approved `keys` from the reviewed scan when approval names specific devices. Unattended setup skips the password prompt and can return an admin token; protect the output and switch to a read token for monitoring.

### Rules you must follow

- **Ask before you change anything on a miner.** Restart, pause and pool changes interrupt hashing and are audited. Bulk actions preview by default (`dry_run: true`): show the user the preview first.
- **Never guess credentials**, node RPC logins, payout addresses or passwords. If you need one, ask.
- **A wrong payout address loses a found block.** When changing a miner's pool, read the address back to the user.
- Keep secrets and wallet addresses out of chat and logs; use secure app fields and a private confirmation view. Ask before firmware changes, deleting data or other destructive actions too.
- Frequency/voltage ("tuning") is off until the user enables `safety.allow_tuning`. Do not turn it on for them.
- Read-only tokens are enough for monitoring. Use `control` only when the user asked for an action, and never `admin` unless you are doing setup.
- Honest odds: solo mining is a lottery. Do not tell users they are "close" or "due". The app's `plain_english` field is worded carefully; reuse it.
- `horizons.ten_minutes` is **Next 10 minutes**: the Poisson chance of at least one block in a fixed 600-second window, not the chance to win the very next network block. Live and what-if responses share it; a device estimate uses observed TH/s as the what-if override. Zero is zero; missing difficulty is unavailable. The difficulty-one factor is `2**48 / 65535`, not the `2**32` approximation.
- Network `field_sources` preserves each selected field's observation time and staleness. A fresh unrelated source cannot refresh old difficulty. A found-block address match is monitoring evidence, not payout proof.
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
.venv/bin/python -m pytest               # backend tests; live-hardware tests need BSMM_LIVE=1
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
- **Every control action goes through `Fleet.run_action`**. Its per-device lock coordinates polling, updates and removal. Recheck permissions, enabled/removal state and identity after queued waits. Admitted actions settle and are audited before cancellation releases the lock; cancelled waiters never execute. Different devices remain independent.
- **Transaction ownership is task-local.** All runtime database writes use `Database.tx()`, including direct connection users. Same-task nested scopes join the outer transaction; never hand its connection to another task or commit/rollback directly. Only the outer owner settles commit/rollback, including cancellation. Reads/backups use database helpers or `read_connection()`; bootstrap/migrations precede runtime use.
- Validate device updates on a copy and persist before replacing runtime state. Alias merges use current locked state. Contradictory MAC/serial identities are not aliases; AxeOS compares saved and reported identities on polling and fresh pre-control reads. Missing identity retains endpoint-only compatibility, not authentication. Preview and execution share parameter validation; previews never write controls/audit, and unavailable tuning ranges or unsupported controls fail closed.
- Fleet owns buffered/in-flight samples: serialize flush/removal, commit raw samples and rollups together, settle work before final shutdown flush, and retain failed batches. History retention drains pending samples; deletion filters pending rows and deletes history after preceding writes.
- Preserve zero telemetry and actual observation times. History averages use per-metric valid counts from additive migration 2; never rewrite released migration 1 or infer valid counts from total rows. Preserve legacy unknown-count warnings and choose retained tiers for old windows. See `docs/ARCHITECTURE.md`.
- Alerts replay the event store with a persisted cursor and per-rule receipts; the bus is only a wakeup. Apply scopes before cooldown and reject nonfinite numeric rules. External delivery is at-least-once across interrupted acknowledgements, bounded by retention. Incomplete coinbase reads hold the contiguous block watermark for bounded retry.
- Saved-settings recovery preserves valid explicit authentication or fails closed; malformed preferences never imply passwordless consent. Host authorization uses literal local/private addresses and exact machine/bind/`BSMM_ALLOWED_HOSTS` names, never wildcard or untrusted DNS resolution. `bsmm.internal` is the in-process MCP adapter host. Foreign-Origin writes need a scoped bearer token even without a password; CORS does not grant write authority. These gates remain active in demo mode.
- Enforce the 4 MiB received-body cap before REST/MCP parsing. Imported channels discard canonical secrets and stay disabled until credential re-entry. Validate and persist settings before side effects. SSE revalidates before sensitive events and on one-second idle checks; secret-only source updates rebuild pollers. Cancel and await discovery before closing shared HTTP/database resources.
- Disk `Store.open` normalizes legacy notification config before any consumer can use the store. `CHANNEL_CLASSES` `FieldSpec.secret` is the canonical classification. Move recognized credentials into the existing SecretBox-encrypted column without trimming strings, changing channel metadata/enable state or rotating the key. Preserve nonempty encrypted values over plaintext fallbacks; untouched encrypted payloads stay byte-identical. Normalization is idempotent and uses the existing `Database.tx` connection directly. Unreadable credential data on rows needing normalization must fail startup and roll back, not silently erase a user's credential. New config imports still discard credentials and arrive disabled. This does not erase historical SQLite pages or backups.
- Public-read access is not a signed-in account. Logout/401 clears protected caches and identity synchronously, aborts requests/streams, rejects late responses and unmounts protected pages. Keep sign-in reachable; label unconfirmed server logout honestly. Form drafts use captured baselines, refresh untouched fields, PATCH only edits and expose observed same-field conflicts. Dashboard edit mode and its draft share one lifetime.
- Monitoring errors mean unknown/stale, not healthy-empty. Bind chart data to its successful query and retain last-success time on failed refresh. Notification draft tests require Save first and setup retests reuse channel IDs; browser fixtures never deliver real notifications. Read-only appearance uses validated browser-local overrides without server PATCHes; admin preferences remain server-owned.
- **Test the control.** A test that would still pass with the bug present proves nothing; make it fail first.
- Packaging: build the UI before default `uv build`. Keep generated `src/bsmm/web/**` in the shared Hatch build artifacts so both the sdist and its wheel contain the real UI. Verify index/assets in both archives and a wheel rebuilt from the sdist; retain the release workflow's wheel-content assertion. See `docs/PACKAGING.md`.
- Documentation: `src/bsmm/agent_docs.py` owns setup preflight, recipe and safety guidance for the JSON guide and served text. Regenerate root `llms.txt` with `scripts/gen_llms_txt.py`; never hand-edit it. Keep platform installation on verified GitHub artifacts until PyPI publication is verified. Version changes update `src/bsmm/__init__.py` and the web package/lock root metadata, then check `uv lock --check` without dependency upgrades. Preserve historical release notes and distinguish candidate documentation from a verified release.
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

### Lifecycle, Windows and release boundaries

- `src/bsmm/cli/lifecycle.py` owns background identity: `bsmm.pid` is a JSON PID/creation-time/executable/command-line/data-directory/nonce/port record. `bsmm.lock` serializes start/stop; never unlink its inode. Ready/stop files carry the nonce. Use non-destructive psutil checks and cooperative shutdown, never PID-only signals or image-wide taskkill. Legacy unverified state is cleaned without stopping a process; start requires retry, and shutdown timeout retains identity. Platform-managed foreground services have a separate owner.
- `bsmm password` uses the API's current-password gate (`--current-password`, `BSMM_CURRENT_PASSWORD` or hidden prompt). Unreachable targets fail closed; local recovery requires explicit `--offline-local --data-dir`, incompatible with URL targeting. Service commands check manager exits and retain definitions after failed unregister; launchd arguments use plistlib.
- `installer/windows/` builds current Python/Vue with PyInstaller onedir and per-user Inno Setup. Derive versions from `src/bsmm/__init__.py`, build Vue first, and preserve user data/key on upgrade/uninstall. `.github/workflows/windows.yml` supplies artifacts to release only after native smoke passes. Linux/static checks do not prove Windows acceptance. Optional Apprise/mdns/tray extras are not bundled; see `installer/windows/README.md`.
- `installer/windows/smoke.py` requires `--legacy-source` pointing to a separate clean checkout of immutable v1.1.1 commit `5674faad417911c92c526ebf5bf78a57b09ed1af`. `legacy_seed.py` uses that checkout's verified Store/Auth imports without starting an old server. The installed candidate must be the first candidate executable to open those data; compare logical records and exact credential preservation, not database-file bytes across schema migration. The native smoke also requires actual frozen cold `setup --yes --json` in empty owned data, literal loopback CIDR and owned discovery ports; refuse rather than contacting an installed service when a port is unavailable, and never log setup token output. This is v1.1.1 data-upgrade acceptance, not an old Windows-installer upgrade or v0.9.3 GUI/history migration.
- Windows CI derives isolated build/cache paths from runtime `RUNNER_TEMP` in the first PowerShell step and writes `GITHUB_ENV` before tools run. Do not use `runner.temp` in job-level `env`. Run real actionlint against every workflow; syntax/string tests alone do not validate GitHub expression contexts.
- Native resource/shortcut diagnostics expose only fixed stages, bounded version strings and match booleans through `smoke.py`'s allowlist. Never print arbitrary child output, arguments or exceptions; setup output can contain a token. Browser CI must install both Chromium and Firefox: the frontend-repairs cases explicitly use Firefox and must not be skipped or reassigned to hide missing browser dependencies.
- Inno Setup space-pads textual version resource buffers. The native verifier removes only trailing ASCII spaces from installer text, checks canonical product text and four-part file text, and independently requires both fixed numeric tuples; executable text stays exact. Version equality is ordinal, never PowerShell's culture comparison that ignores embedded NULs. `installer/windows/test-check-native.ps1` exercises positive/negative synthetic resource cases on Windows before the separate real installer smoke. These fixtures are not installation proof.
- Shortcut targets must resolve through opened Windows file handles to the exact installed executable (`installer/windows/native-path.ps1`); hosted-runner directory junctions can give the same file different path text. Matching bytes or basename is not identity. Keep per-user Programs lookup and exact argument checks; disposable junction/copy/missing-file regressions complement real installed-shortcut verification.
- Installer byte-preservation snapshots include SQLite WAL/SHM sidecars and are captured after the credential observer: even a `mode=ro` connection can create those sidecars. Do not attribute observer-created files to the installer or exclude them from comparison. Snapshot diagnostics contain only fixed filenames/change kinds, never data, keys, hashes or arbitrary names.
- Browser tests/screenshots pass `web/scripts/demo-preflight.mjs` before fixture access. Use an owned loopback `--demo --offline` backend and matching BASE / BSMM_DEV_API. `npm run shots` uses the guarded generator; `-- --list` needs no browser. Default output is disposable `web/test-results/screenshots`, not documentation.
- v1.1.2 includes the legacy notification-secret repair and Windows cold-setup/v1.1.1-data-upgrade acceptance source. README screenshots show the current simulated fleet, not hardware measurements. Release requires independent integrated review, exact-byte public-copy review, native Windows build/install/cold setup and v1.1.1 old-data-upgrade proof, plus verification of the immutable release tag, assets and downloads. Linux fixture checks do not waive native port ownership or prove installed Windows behavior. No live installation or hardware proof follows from fixtures.

### Startup alert baseline and history projection

- `AppContext.start` must await `AlertEngine.prepare_event_cursor` before starting any event producer. Preparation transactionally initializes only an absent cursor to the retained event maximum (zero for an empty log), preserving an existing cursor including zero. Start alert evaluation after fleet/network initialization; do not move the evaluator earlier just to prepare the baseline. New startup events remain replayable without replaying historical notifications on first initialization. Existing bounded batches, cooldowns and attempt receipts retain their authority; this is not exactly-once provider delivery.
- Device-history responses keep the flattened per-device series and carry the same conditional legacy unknown-count warnings as fleet history. The registered MCP `get_history` tool with `miner_id` forwards this response; do not infer missing metric counts or discard retained numeric rows.
