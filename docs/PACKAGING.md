# Installing and shipping Solo Miner Monitor

## For users

Pick the one that matches your computer. All of them give you the same app on port **8420**.

An agent can handle installation and setup using the [copyable README prompt](../README.md#let-your-agent-do-the-setup). Use artifacts from the [official stable release](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/latest).

### Docker (best for a NAS, Raspberry Pi, Umbrel-style box or home server)

```bash
curl -O https://raw.githubusercontent.com/smokeysrh/bitcoin-solo-miner-monitor/main/docker-compose.yml
docker compose up -d
```

Open `http://<that computer>:8420`.

- **Linux:** the compose file uses `network_mode: host` so the app can see your miners and scan the network.
- **Docker Desktop (Windows, macOS):** for a portable setup, remove `network_mode: host`, enable the `ports:` lines, then add miners by address or type your private range (for example `192.168.1.0/24`) into the scan box.
- Images are published for `linux/amd64` and `linux/arm64` (Raspberry Pi 4/5) at `ghcr.io/smokeysrh/bitcoin-solo-miner-monitor`.
- Data lives in the `bsmm-data` volume. Back it up from **Settings → Data & backup**.
- To require a password from the first start, set `BSMM_ADMIN_PASSWORD` in the compose file.

### Windows installer

Download the Windows installer attached to the [v1.1.2 release](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/tag/v1.1.2). Follow its setup steps, launch the app and open the dashboard. Keep the existing data directory when upgrading. The v0.9.3 installer belongs to the older app; use the legacy instructions below for that installation.

### Python wheel with pipx (Windows, macOS, Linux)

Install Python 3.11 or newer and pipx, then use the versioned GitHub wheel:

```bash
pipx install https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/download/v1.1.2/bitcoin_solo_miner_monitor-1.1.2-py3-none-any.whl
bsmm setup                                   # interactive setup; review the discovered miners before accepting
```

The wheel is distributed through GitHub Releases. Choose its `.whl` asset rather than asking pipx to find the package on PyPI. For a hardware-free preview after installation, run `bsmm demo`.

Apprise is an optional Python extra and is not bundled in the Windows installer. To include it in a new pipx installation, use:

```bash
pipx install 'bitcoin-solo-miner-monitor[apprise] @ https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/download/v1.1.2/bitcoin_solo_miner_monitor-1.1.2-py3-none-any.whl'
```

`bsmm start` / `bsmm stop` control the background server. `bsmm service install` previews autostart configuration; `bsmm service install --apply` installs it after you approve (a systemd user unit, a launchd agent, or a Windows scheduled task). Ask before changing an existing service.

`bsmm password` changes the password through the target API and asks for the current password when required. An unreachable server is not permission to bypass authentication. Deliberate local recovery uses `bsmm password --offline-local --data-dir <existing-data-directory>` after the operator approves; do not combine it with a URL target.

### Agent setup and unattended commands

Read the running app's `/llms.txt` or `/api/v1/agent/guide` first. Set authentication for the network, keep secrets in secure app fields, and preserve existing settings. Ask only for missing RPC credentials, electricity price or alert preferences. Use a `read` token for routine monitoring; setup may need `control` or `admin` temporarily.

For discovery without adoption, use `bsmm discover --cidr 192.168.1.0/24 --json` with the user's actual private range. Show the miner and source candidates, then wait for confirmation. The guide's API flow can adopt selected `host:port` keys from that scan.

`bsmm setup --yes` skips confirmation and can adopt all newly found miners and connect a discovered Public Pool. Use it only after the user approves that behavior and scan range. It scans again, so use the API flow when approval is limited to specific candidates. `--yes` also skips the password prompt: arrange authentication first. Its output can contain a new admin token; keep it out of chat and logs, then use a read-scoped token for monitoring. Ask before miner controls, pool or payout changes, tuning, firmware changes or deletion.

### Upgrades and backups

Before replacing the app, download a database backup from **Settings → Data & backup**. Keep a protected copy of `secret.key` (or your configured `BSMM_SECRET_KEY`) too; the database download omits the key. See [SECURITY.md](../SECURITY.md#secrets). Preserve the whole data directory and existing miner configuration. `BSMM_DATA_DIR` selects a custom data directory; `bsmm doctor` reports the current one.

For a wheel installation, stop the existing app through its normal launcher or service after approval, then reinstall from the versioned wheel URL above with `pipx install --force <wheel-url>`. Start it with the same data directory and verify `bsmm version`, `bsmm doctor` and `bsmm status` before continuing. For Docker, keep the same `bsmm-data` volume mounted while pulling and recreating the container; avoid volume-removal commands.

### Coming from v0.9.x

The v0.9.3 Windows installer placed the program under `Program Files\Bitcoin Solo Miner Monitor` and user data under `%APPDATA%\Bitcoin Solo Miner Monitor`. Preserve that data folder before installing the rebuilt app. Find the old `config.db` and keep its companion `-wal` and `-shm` files with it if present.

After starting the new app, and after confirming which miners to import:

```bash
bsmm migrate-legacy path/to/old/data/config.db --url http://localhost:8420
```

This reads a private copy of the legacy database and imports miner hosts, ports and names. It probes each miner and reports the result; the original database stays untouched. Historical telemetry, charts, alert settings and credentials remain in the old installation. Keep that archive for reference and configure those settings in the new app. Automatic v0.9.x history migration is unsupported.

### Umbrel / Start9 / other node OSes

A starting-point app definition for Umbrel is in [`packaging/umbrel/`](../packaging/umbrel). It has not been run on a real Umbrel yet, so treat it as a template. On any node OS you can already run the Docker image; the app will find a Public Pool or Bitcoin Core on the same network during the scan.

## Settings you can pass as environment variables

| Variable | Meaning |
| --- | --- |
| `BSMM_PORT` / `BSMM_HOST` | Where to listen (default `8420` on all addresses) |
| `BSMM_DATA_DIR` | Where the database lives (`/data` in Docker) |
| `BSMM_ADMIN_PASSWORD` | Set the dashboard password at start-up. Never logged |
| `BSMM_AUTH` | `none` or `password`; wins over what the setup wizard stored |
| `BSMM_OFFLINE=1` | Disable automatic public network-data, price and release checks; configured sources and alert destinations still make requests |
| `BSMM_NO_UPDATE_CHECK=1` | Skip only the update check |
| `BSMM_SERVE_UI=0` | API and MCP only, no web interface |
| `BSMM_TRUSTED_PROXIES` | Comma-separated proxy IPs whose `X-Forwarded-For` is believed (rate limiting by real client) |
| `BSMM_CORS_ORIGINS` | Extra browser origins allowed to call the API (the bundled UI needs none) |
| `BSMM_ALLOWED_HOSTS` | Exact custom DNS/reverse-proxy hostnames, comma-separated, without scheme/port/path; no wildcard |
| `BSMM_LOG_LEVEL`, `BSMM_DEMO` | Verbosity; run a simulated fleet |

Literal local/private IPs, localhost and the machine's own hostname are supported without a custom Host entry. CORS allows response sharing, not ambient write access: deliberate foreign-origin writes need an explicitly scoped bearer token even when passwordless mode is selected.

## For maintainers

### Local builds

```bash
cd web && npm ci && npm run build     # writes the UI into src/bsmm/web
cd .. && uv build                     # wheel + sdist in dist/, UI included
docker build -t bsmm:dev .
```

The UI is **not committed**: `src/bsmm/web/` is generated. A source checkout without a build shows a friendly page explaining that.

Default `uv build` creates the sdist first, then builds the wheel from it. The shared `[tool.hatch.build]` artifacts rule includes the generated UI in both formats despite Git ignoring it; a wheel-only rule loses the UI at the sdist boundary. Keep the sdist exclusions for `web/node_modules` and `web/dist`, and do not include caches or runtime data.

Before release, check that both archives contain `index.html` and actual files under `assets/`, then extract the sdist and run `uv build --wheel <extracted-directory> --out-dir <clean-output-directory>`. That wheel must preserve the same UI without needing Node or another UI build. Install the built wheel in a disposable environment and verify the version, offline demo health, HTTP index and its JS/CSS assets. The release workflow's existing wheel-content assertion remains a mandatory gate.

### Releasing

1. Update `src/bsmm/__init__.py` (`__version__`), the web package/lock root versions, Umbrel template version/image tag and `CHANGELOG.md`. Regenerate `llms.txt` with `python scripts/gen_llms_txt.py`; check `uv lock --check` and preserve locked dependency versions. The local project entry may use dynamic version metadata rather than a literal version in `uv.lock`.
2. Verify the integrated v1.1.2 candidate: focused repair regressions, backend/web suites, built wheel and sdist UI contents, and native Windows install/launch/upgrade/data preservation. Check `ten_minutes` covers 600 seconds and the UI says **Next 10 minutes**. Refresh screenshots against a disposable demo only. Review the exact public docs and final asset filenames before publication.
3. After release approval and verification, create and push `v1.1.2`. Never move or replace a published tag: v1.1.0 remains the failed packaging attempt.
4. `.github/workflows/release.yml` handles GitHub release artifacts and the multi-architecture image at ghcr.io. Read back the published assets, wheel URL and container tags. Verify the Windows installer is attached to the same release before announcing it. The v1.1.1 wheel and image were published; the current candidate still needs its own checks.

### Publishing to PyPI (one-time setup)

PyPI publication is optional and currently disabled. Keep user installation instructions on GitHub artifacts until an actual PyPI release is verified.

1. On pypi.org, add a **trusted publisher** for this repository: workflow `release.yml`, environment `pypi`.
2. In the GitHub repository settings create the environment `pypi` and the repository variable `PUBLISH_PYPI=true`.

No API token is stored anywhere; PyPI trusts the workflow's identity.

### What CI checks

Python 3.11/3.12/3.13: ruff, strict mypy, the full test suite, and that `llms.txt` matches its generator. Web: type-check, unit tests, icon check, production build. Then a browser run against a simulated fleet (Playwright, desktop and phone sizes, plus an accessibility audit with axe), and a Docker build that must reach `healthy`.
