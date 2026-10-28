# Windows distribution (current Python/Vue application)

This directory builds the current `bsmm` app, not the retired v0.9 Electron/Flask
installer. The old installer required admin access, targeted `run.py` and
`src/frontend`, and used image-wide Python termination. None of that is used here.

## Install and use

Use the Windows setup executable from a release whose native Windows smoke job
passed. It installs for the current user, under LocalAppData/Programs; no admin
prompt, Python installation or Node installation is required to run the app.
Start-menu entries start the dashboard, stop its managed background instance,
open the generated agent guide, and uninstall the app.

The portable zip is the same executable and dependencies without installation.
Extract the **whole** `bsmm` directory, including `_internal`; do not move just
`bsmm.exe`. From that folder:

```powershell
.\bsmm.exe version
.\bsmm.exe start --open
.\bsmm.exe agent-guide
.\bsmm.exe stop
```

The installer does not automatically register a Windows service or scheduled
task. `bsmm service install` previews that separate opt-in operation; `--apply`
performs it and fails visibly if Task Scheduler refuses it. An independently
started foreground/service instance must be stopped through its own owner.

Persistent data is separate from the program: normally
`%LOCALAPPDATA%\bitcoin-solo-miner-monitor`, or the selected `BSMM_DATA_DIR` /
`--data-dir`. The database and `secret.key` belong together. Repair/reinstall and
uninstall preserve both, including passwords and encrypted credentials. There is
no data-purge uninstall option. A failed safe stop aborts installation/removal.
The old v0.9 installation is not auto-deleted or auto-migrated; use the explicit
`migrate-legacy` command if needed, after keeping its original data.

Old PID-only files are deliberately not shutdown authority. The CLI removes
unverified state and tells you that it did **not** stop that process. Check for an
old running server before retrying start. It never kills all Python processes.
A shutdown timeout preserves identity for retry rather than forcing a kill.

The bundle includes the required Python dependencies and built Vue assets. The
optional `mdns`, `apprise` and `tray` extras are not in this minimal distribution.
The agent guide is generated from the same source served at `/llms.txt`.
Builds are unsigned; Windows may show a reputation warning. No signing or
SmartScreen reputation claim is made.

## Build and verify on a disposable native Windows runner

Requirements: Python 3.12 / uv, Node 22, and Inno Setup 6 (`ISCC.exe`). The workflow
installs build prerequisites on the disposable runner, not on an end user's PC.

```powershell
$env:BSMM_LIVE = '0'
$env:BSMM_OFFLINE = '1'
$env:BSMM_NO_UPDATE_CHECK = '1'
$env:UV_PROJECT_ENVIRONMENT = "$env:TEMP/bsmm-build-venv"
$env:UV_CACHE_DIR = "$env:TEMP/bsmm-build-cache/uv"
$env:PYINSTALLER_CONFIG_DIR = "$env:TEMP/bsmm-build-cache/pyinstaller"
uv sync --frozen --extra dev --python 3.12
npm --prefix web ci --no-audit --no-fund
npm --prefix web run build
uv run --no-sync python installer/windows/build.py --installer --output dist/windows
$version = uv run --no-sync python installer/windows/build.py --version
git worktree add --detach ../bsmm-smoke-v1.1.1 5674faad417911c92c526ebf5bf78a57b09ed1af
uv run --no-sync python installer/windows/smoke.py --exe dist/windows/portable/bsmm/bsmm.exe --installer "dist/windows/bsmm-$version-windows-setup.exe" --expected-version $version --legacy-source ../bsmm-smoke-v1.1.1
```

Check each command's exit code (the workflow does). `src/bsmm/__init__.py` is the
version authority for the executable, resource metadata, installer and names;
do not pass a separate invented release version. The integration owner must
apply the release version change before building that release.

`.github/workflows/windows.yml` supports manual candidate runs and is reused by
the tag release workflow. Manual `expected_version` defaults to **1.1.2** and
rejects unbumped source. The tag release waits for Windows smoke before attaching
its installer, portable zip and SHA256SUMS to the GitHub release. Building or
reviewing this source does not dispatch a workflow or publish a release.

Smoke checks use isolated data/home, offline mode, reserved loopback ports and an
unrelated sentinel child. They check executable version and PE resources, health
version, real Vue JS/CSS and agent-guide assets, repeated-start identity,
cooperative stop, stale PID refusal, occupied-port startup failure, shortcuts,
install/reinstall while running, persistent password/key preservation and
uninstall. A separate empty data directory exercises the actual installed
`setup --yes --json --cidr 127.0.0.1/32 --port <reserved-port>` command from cold
state. Stdout must be exactly one JSON document; its generated bearer token is
discarded, never logged. The harness owns all discovery TCP ports without
listening and refuses to run setup if any cannot be reserved. This keeps the
real discovery path away from installed services. Offline/no-update mode,
no configured sources, disabled fixture device/channel and the absence of mDNS
calls keep these checks off the LAN and external providers. On Linux, reserving
port 80 may be denied; do not weaken this gate or probe an existing service.

The separate pinned v1.1.1 checkout seeds synthetic device/settings/history,
password and encrypted notification data through its own Store/Auth code;
commit, imported version and module locations are checked. No old server runs.
After silent installation into a fresh target, installed `bsmm.exe start` is the
first candidate to open that data directory. The smoke checks the candidate
schema and old logical values (not database-file equality), exact password/key
and decrypted credential preservation, reopen, same-candidate reinstall and
uninstall-data retention. Schema versions are reported honestly; an unchanged
schema is not a claim that an ALTER migration ran.

This is **v1.1.1 data upgrade**, not a previous v1.1.1 Windows-installer upgrade:
there was no such Windows asset. It does not migrate the retired v0.9.3 GUI
state/history or remove that application. CI obtains the immutable source with
a separate checkout; local replay can use the detached worktree above. Retire
that fixture only after retaining the required acceptance evidence. Linux
source/frozen smoke is useful packaging evidence, **not** native Windows
installer evidence. Only a successful native candidate run closes that gate.
