# Changelog

All notable changes to Bitcoin Solo Miner Monitor will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/0.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-10-27
A ground-up rewrite. The 0.9 code base is gone; see [docs/AUDIT.md](docs/AUDIT.md) for why. (`1.0.0rc1` was the development build of this release and was never published.)

### Added
- **Fleet monitoring** for AxeOS miners (Bitaxe, NerdQAxe, and relatives) and cgminer-API miners (Avalon, Antminer, Braiins), with automatic discovery, fingerprinting and live updates over Server-Sent Events.
- **Sources**: Bitcoin Core (RPC), Public Pool, ckpool, mempool.space.
- **Odds and economics** in plain English: block probability per day/month/year, electricity cost, J/TH, break-even.
- **Control** with safety rails: restart, identify, pause/resume, pool change, fan, opt-in frequency/voltage. Bulk actions preview first; everything is audited.
- **Alerts**: 15 rule types, 8 channels (Discord, Telegram, ntfy, Slack, Pushover, email, webhook, Apprise), quiet hours, cooldowns, "Resolved" messages. Active alert state survives restarts.
- **New UI**: customizable dashboard (16 widgets, drag to arrange), miner pages, analytics, Bitcoin page, odds page, setup wizard, kiosk mode, command palette, PWA install, phone layout, dark / black / light themes with axe-checked contrast.
- **Agent support**: `/llms.txt`, MCP server (27 tools), scoped API tokens, OpenAPI with actionable error hints, unattended CLI (`bsmm setup --yes`, `bsmm status --json`, `bsmm doctor`), `AGENTS.md` and a skill.
- **Demo mode** (`bsmm demo`) with simulators of real miners.
- **History** stored as 1-minute, hourly and daily rollups.
- `bsmm migrate-legacy` imports miners from a 0.9 database.
- Docker image (amd64, arm64), compose file, Umbrel template (untested), CI and release workflows (not yet run on GitHub).

### Miner identification
Based on the `feature/home-miner-identification` work on the 0.9 code base, ported to the new drivers.
- Models are named from what the device reports, in a fixed order, with a confidence and the evidence: ESP-Miner's board-version table for stock Bitaxe boards (Max, Ultra, Hex, Supra, Gamma, Gamma Duo, Supra Hex, GT, Naja Duo, Gamma Hex), the firmware's own family name, forks (NerdQAxe, NerdAxe...) kept as they name themselves, Lucky Miner LV06/LV07/LV08 and Magic Miner BG02 by hostname or chip layout. Hashrate never decides a model.
- A chip layout shared by several families (2x BM1370) is reported as ambiguous instead of guessed. A Bitaxe Gamma on board 602 can no longer be taken for a Hex.
- Avalon Nano 3 / 3S, Mini 3, Q and full-size models are named from the cgminer reply; other cgminer devices are never labelled Avalon.
- The miner page shows why the app chose a model, and says "best guess" when it is not sure.
- New `bsmm capture <host> [--out FILE]`: read-only, shows how a miner was recognised and saves its raw replies with Wi-Fi name, MAC, serial, pool users and wallet addresses removed, for adding support for new models. See [docs/miner-identification.md](docs/miner-identification.md).

### Changed
- Python 3.11+, FastAPI, SQLite (WAL), Vue 3 + TypeScript + Tailwind v4.
- Secrets (RPC logins, webhook URLs, bot tokens) are encrypted at rest and write-only.
- The app is open on first start and offers to set a password in setup.

### Removed
- The Windows installer. Use `pipx` or Docker Desktop.
- The old REST API. The new one lives at `/api/v1`.
- The hard-coded `Bearer dev-key-12345` development key that the 0.9 frontend sent and the backend accepted.
- Roughly 1,000 tracked files of debug scripts, data dumps, a committed SQLite WAL, duplicated source copies and an unused easter-egg module.

### Fixed (found during the rewrite)
- A Bitcoin Core node that refuses this computer (`rpcallowip`, HTTP 403) was reported as "wrong user name or password". It now says the node refused the computer, names this computer's address and suggests the `rpcallowip` line to add.
- On phones the miners table view widened the whole page.
- Demo mode crashed on start when rollup rows had different columns; unknown columns are now rejected explicitly.
- A fresh demo showed a 40% reject rate off five shares.
- Fleet "performance" was misleading with a mixed fleet; it is now computed only over miners that report an expected hashrate.
- Loopback scans were silently skipped even when asked for.
- Telegram messages could break on `<`/`&`; HTML is escaped after trimming. A 3xx reply from a webhook now counts as a failure.
- `migrate-legacy` missed changes still sitting in the old database's WAL file.
- A missing `.js`/`.png` was answered with the app's HTML page instead of a 404.
- Light-theme status colours failed contrast; table sort state is announced to screen readers.

### Known gaps
- Only the NerdQAxe++ and Magic Miner BG02 were tested on real hardware. Other families are covered by recorded replies and simulators.
- No one-click Windows installer.
- The Umbrel template and release workflows have not been run.

## [0.9.2] - 2025-10-27

### 🚀 Major Improvements

#### Windows Installer Refactoring

- **Complete installer system overhaul** for simplicity, speed, and reliability
  - Consolidated 3 installer scripts into 1 unified `installer.nsi`
  - Eliminated 6 configuration files and complex macro dependencies
  - Reduced installation time from 5-10 minutes to under 60 seconds
  - Pre-bundled Python runtime for offline installation (no internet required)
  - Single source of truth for version management (`src/backend/version.py`)
  - Automated build process with `build.ps1` script
  - One-time bundle preparation with `prepare-bundle.ps1`
  - Inline launcher creation (prevents bugs from forgotten macro calls)
  - Comprehensive error handling and verification
  - Improved uninstaller with user data preservation options

### 🐛 Bug Fixes

- **Critical**: Fixed Windows installer not launching app after installation
  - Resolved through complete installer refactoring
  - Improved launcher batch file with instance checking and browser auto-launch
  - Added 3-second startup delay for proper server initialization
  - Added helper scripts and documentation for installer fix
  - Updated .gitignore to exclude installer build staging directories

### 🧹 Code Cleanup

- **Installer System Cleanup**
  - Removed old installer scripts (`installer_enhanced.nsi`, `installer_final.nsi`)
  - Removed old build scripts (`build_installer.bat`, `build_final_installer.bat`)
  - Removed entire `config/` directory with legacy .nsh files
  - Removed entire `scripts/` directory with unused Python scripts
  - Removed test installer executables from repository
  - Cleaned up redundant and unused code
- **Project Organization**
  - Organized project documentation into proper folder structure
  - Moved bug reports to `docs/bug-reports/`
  - Moved investigations to `docs/investigations/`
  - Moved development docs to `docs/development/`
  - Moved implementation summaries to `docs/implementation-summaries/`
  - Moved all test files to `tests/` directory
  - Updated `.gitignore` to exclude development-only folders from releases
  - Cleaned up root directory for better project organization

### 📚 Documentation

- Created comprehensive installer documentation (`installer/windows/README.md`)
  - Architecture overview and component descriptions
  - Detailed build and preparation instructions
  - Testing procedures and troubleshooting guide
  - Version management documentation
  - Advanced topics (code signing, silent install, portable version)
- Updated `BUILD_INSTALLER_FOR_RELEASE.md` with new build process
- Created `INSTALLER_MIGRATION_GUIDE.md` explaining changes from old system
- Added cleanup summary documentation

### 📦 Release Preparation

- Updated version to 0.9.2 across all files
- Added backend version management system
- Prepared codebase for production release
- Streamlined build and release process

## [0.9.1] - 2025-10-25

### 🐛 Bug Fixes

- **Critical**: Fixed MinerDetail page refresh bug that caused blank screen on page reload
  - Replaced problematic VSkeletonLoader with simple loading indicator
  - Improved template structure for better null safety
  - Added proper loading state handling when store is empty
- Resolved Vue rendering errors on component initialization
