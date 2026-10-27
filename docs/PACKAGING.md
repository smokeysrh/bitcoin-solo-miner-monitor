# Installing and shipping Solo Miner Monitor

## For users

Pick the one that matches your computer. All of them give you the same app on port **8420**.

### Docker (best for a NAS, Raspberry Pi, Umbrel-style box or home server)

```bash
curl -O https://raw.githubusercontent.com/smokeysrh/bitcoin-solo-miner-monitor/main/docker-compose.yml
docker compose up -d
```

Open `http://<that computer>:8420`.

- **Linux:** the compose file uses `network_mode: host` so the app can see your miners and scan the network.
- **Docker Desktop (Windows, macOS):** host networking is not available. Remove `network_mode: host`, enable the `ports:` lines, then add miners by address or type your range (for example `192.168.1.0/24`) into the scan box. Everything else works the same.
- Images are published for `linux/amd64` and `linux/arm64` (Raspberry Pi 4/5) at `ghcr.io/smokeysrh/bitcoin-solo-miner-monitor`.
- Data lives in the `bsmm-data` volume. Back it up from **Settings → Data & backup**.
- To require a password from the first start, set `BSMM_ADMIN_PASSWORD` in the compose file.

### pipx (Windows, macOS, Linux desktop)

```bash
pipx install bitcoin-solo-miner-monitor      # once the package is on PyPI; until then use the wheel from the GitHub release
bsmm setup                                   # starts it, finds your miners, asks about your electricity price
```

Python 3.11 or newer. `bsmm start` / `bsmm stop` control the background server. `bsmm service install --apply` makes it start by itself when you log in (a systemd user unit, a launchd agent, or a Windows scheduled task). Without `--apply` it only prints what it would do.

> Windows: there is no one-click installer for 1.0. `pipx` or Docker Desktop are the supported routes. (The old 0.9 Windows installer is gone on purpose; see CHANGELOG.)

### Umbrel / Start9 / other node OSes

A starting-point app definition for Umbrel is in [`packaging/umbrel/`](../packaging/umbrel). It has not been run on a real Umbrel yet, so treat it as a template. On any node OS you can already run the Docker image; the app will find a Public Pool or Bitcoin Core on the same network during the scan.

## Settings you can pass as environment variables

| Variable | Meaning |
| --- | --- |
| `BSMM_PORT` / `BSMM_HOST` | Where to listen (default `8420` on all addresses) |
| `BSMM_DATA_DIR` | Where the database lives (`/data` in Docker) |
| `BSMM_ADMIN_PASSWORD` | Set the dashboard password at start-up. Never logged |
| `BSMM_AUTH` | `none` or `password`; wins over what the setup wizard stored |
| `BSMM_OFFLINE=1` | Never contact the internet (no mempool.space, prices or update check) |
| `BSMM_NO_UPDATE_CHECK=1` | Skip only the update check |
| `BSMM_SERVE_UI=0` | API and MCP only, no web interface |
| `BSMM_TRUSTED_PROXIES` | Comma-separated proxy IPs whose `X-Forwarded-For` is believed (rate limiting by real client) |
| `BSMM_CORS_ORIGINS` | Extra browser origins allowed to call the API (the bundled UI needs none) |
| `BSMM_LOG_LEVEL`, `BSMM_DEMO` | Verbosity; run a simulated fleet |

## For maintainers

### Local builds

```bash
cd web && npm ci && npm run build     # writes the UI into src/bsmm/web
cd .. && uv build                     # wheel + sdist in dist/, UI included
docker build -t bsmm:dev .
```

The UI is **not committed**: `src/bsmm/web/` is generated. A source checkout without a build shows a friendly page explaining that.

### Releasing

1. Update `src/bsmm/__init__.py` (`__version__`) and `CHANGELOG.md`.
2. `git tag v1.1.0 && git push --tags` (pre-releases: `v1.2.0-rc.1`).
3. `.github/workflows/release.yml` checks the tag matches the version, builds the UI and the package, verifies the wheel contains the UI, attaches both to a GitHub release, and pushes the multi-architecture image to ghcr.io.

### Publishing to PyPI (one-time setup)

1. On pypi.org, add a **trusted publisher** for this repository: workflow `release.yml`, environment `pypi`.
2. In the GitHub repository settings create the environment `pypi` and the repository variable `PUBLISH_PYPI=true`.

No API token is stored anywhere; PyPI trusts the workflow's identity.

### What CI checks

Python 3.11/3.12/3.13: ruff, strict mypy, the full test suite, and that `llms.txt` matches its generator. Web: type-check, unit tests, icon check, production build. Then a browser run against a simulated fleet (Playwright, desktop and phone sizes, plus an accessibility audit with axe), and a Docker build that must reach `healthy`.
