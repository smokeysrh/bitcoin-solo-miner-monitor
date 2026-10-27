# Audit of the 0.9.x code base

Why 1.0 is a rewrite and not a patch. This is what the old tree looked like when the rewrite started (v0.9.3, Python + Vue 3 + a Windows installer).

## Findings

| Area | Finding | What 1.0 did |
| --- | --- | --- |
| Security | `Bearer dev-key-12345` was hard-coded in the frontend's settings service and added to the backend's valid keys (`security_middleware.py`). Anyone who read the source had admin access. | Removed. Scoped, hashed API tokens; optional password with scrypt; login throttling. |
| Repo hygiene | ~1,040 tracked files. About 17 stray debug/analysis scripts in the root (`debug_*.py`, `analyze_*.py`, `test_*.py`), raw Bitaxe data dumps (`bitaxe_data_192_168_*.json`), a committed SQLite WAL/SHM (`data/config.db-wal`, `-shm`), and complete copies of the source under `distribution/` and `installer/.../packages/windows/`. | Clean tree: `src/`, `web/`, `tests/`, `docs/`. |
| Dead code | An easter-egg module (CSS, composable, test component, README) duplicated three times. | Dropped. |
| Unfinished work | 14 Kiro specs. `bitcoin-node-integration` was 0 of 46 tasks done; `polling-settings-fix` 12 of 22; `bug-fixes-security-enhancement` 28 of 43. The headline feature (talking to your own node) was essentially unbuilt. | Built: Bitcoin Core, Public Pool, ckpool and mempool.space sources, odds, economics. |
| Install | Windows-only NSIS installer with a bundled Python runtime and its own build scripts. The 0.9.2 changelog is mostly installer rework and "fixed the app not launching after install". | No installer. Docker and `pipx`; honest about it. |
| Model detection | Fingerprinting by string-matching, with several attempts and fix notes (`bitaxe_gamma_hex_detection_fix_final.md`, `AVALON_NANO_FIX_SUMMARY.md`). Wrong guesses were possible. | One registry, conservative: "unknown miner" beats a wrong guess. Fixtures of real replies in tests. |
| Control | Read-only monitoring. | Restart, identify, pause, pool and fan control with safety settings, previews for bulk actions and an audit log. |
| Agents | None. | `llms.txt`, MCP, scoped tokens, OpenAPI with hints, unattended CLI. |
| Tests | Present but tangled with the debug scripts. | ~800 backend tests, simulators of real protocols, vitest, Playwright, axe audits. |

## Domain knowledge kept

The old research was worth keeping and went into the new drivers and fixtures:

- Avalon cgminer output carries a `MM ID0:Summary` block whose key=value pairs (temperatures, fan, `GHSmm`, `WORKMODE`) are parsed into telemetry.
- The Bitaxe family research in `bitaxe_models_research.md` (board versions, ASIC chips, expected hashrate per model) became `drivers/catalog.py`.
- The AxeOS OpenAPI shape (`GET /api/system/info`, `PATCH /api/system`).

## Not carried over, on purpose

- The Windows installer and its build pipeline.
- The old SQLite schema. `bsmm migrate-legacy <config.db>` imports the miners (name, type, address, port) from it; analytics history from 0.9 is not migrated because it was recorded in a different shape and resolution.
- The old REST routes. The new API is `/api/v1` and is described by `/openapi.json`.
