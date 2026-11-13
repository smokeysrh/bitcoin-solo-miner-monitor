# Changelog

All notable changes to Bitcoin Solo Miner Monitor will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/0.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.1] - 2026-11-13

This patch release tidies up the Night Shift look from 1.4.0, with the light theme getting the most fixes, and points the install guide at the latest release. Easier on the eyes, same hurd.

### Changed
- **Charts:**
  - The line charts (miner detail charts, Analytics, the history chart and the wall display chart) now draw hashrate and best-share lines in the brand kit's chart orange instead of your accent colour. Before, those lines were hard to see on the white light theme. In the light theme the chart orange is a darker orange that is easier to see on white (PR #135).
  - With the default orange accent, the hashrate and best-share lines look the same as before in dark and Black. If you picked a custom accent colour, those two lines no longer follow it. The small trend lines on miner tiles and in the miners table still use your accent colour (PR #135).
  - Other lines on those charts changed colour too, in dark and Black as well. Fan speed and WiFi moved from bright cyan to the kit's teal. Board temperature and core voltage moved from pink to the kit's neutral stone colour, so they no longer look like the frequency and pool latency lines (PR #135).
  - On charts with several miners, the miner colours now follow the kit's chart colours, so miners after the first get different colours than before (PR #135).
  - The celebration confetti uses the kit colours (PR #135).
- **Form fields:**
  - Text boxes, dropdowns, text areas and tag fields now show a clearly visible border all the time, in every theme. Before, the stronger border only appeared on hover, and tag fields had the faint one (PR #135).
- **Fallback page:**
  - The page shown when the interface files are missing now uses the Night Shift colours (PR #134).
- **Docs:**
  - The install guide now points to the latest release for the Windows installer and the Python wheel, instead of old v1.1.2 download links (PR #133).
  - The README now says its screenshots were taken on v1.1.2, before the HashHurdr name and Night Shift look, and have not been retaken yet (PR #133).

### Removed
- **Developer tooling:**
  - An old icon generator script that could overwrite the new HashHurdr icons is gone (PR #132).

### Fixed
- **Light theme readability:**
  - The "on" track of a switch and the underline under the selected tab are darker, so they are readable on white (PR #135).
  - The large headline numbers drawn in the orange gradient are darker, so they are readable on white. Dark and Black are unchanged (PR #135).
- **Fonts:**
  - The app now always sends its bundled font files labelled as fonts. On some systems they were sent with the wrong file type (PR #134).

## [1.4.0] - 2026-11-12

This minor release gives the Bitcoin Solo Miner Monitor its new name, HashHurdr, and a Night Shift look, Built for Plebs, By Plebs, with every hash still a fresh ticket.

### Changed
- **Name, logo and icons:**
  - The name you see is now HashHurdr, with the tagline "Built for Plebs, By Plebs" (PR #122).
  - New logo and icons from the approved brand kit: the sidebar logo (dark and light), the top-bar symbol, browser tab icons, phone home-screen and app icons, the Windows installer and app icon, and the README banner. A brand note and the brand policy are in the docs (PR #122).
  - Notifications carry the new name. The email subject prefix is now `[HashHurdr]` (it was `[Solo Miner Monitor]`), and the email sign-off, the Discord webhook sender name and footer, and the ntfy fallback title say HashHurdr too. If you have an email filter on the old subject, update it (PR #122).
  - Nothing technical was renamed: the package `bitcoin-solo-miner-monitor`, the `bsmm` command and service, data and key folders, API paths and fields (apart from the removal below), the Docker image, the Umbrel app id, the Windows install folder and the Start Menu group all stay as they were. An upgrade installs over the existing app in the same place (PR #122).
- **Night Shift look:**
  - New HashHurdr Night Shift colours in all three themes: dark (the default), Black and light. The wall display uses whichever theme you have chosen. Your chosen theme and accent colour are kept (PR #128).
  - Fonts are bundled with the app, with their licences: Saira for headings, Inter for the interface and JetBrains Mono for numbers. The app does not download fonts from the internet (PR #128).
  - Status colours keep their shapes, icons and labels (PR #128).
- **Wording:**
  - The odds, money and glossary screens, the agent guide and the MCP instructions are rewritten as plain lottery talk: every hash is a fresh ticket and nobody is ever "due" (PR #120).

### Removed
- **Break-even Bitcoin price:**
  - The break-even Bitcoin price is gone from the Odds & costs page and the Electricity & value widget. Expected value and electricity cost figures are unchanged (PR #120).
  - The field `economics.break_even_btc_price` is removed from the `/api/v1/odds` response and from the `odds` section of the `/api/v1/overview` response, and so from the MCP tools. Anything reading that field must stop using it (PR #120).

### Fixed
- **Contrast:**
  - In the dark and Black themes, the alert badge had white text on red, which was hard to read. It now has dark text on red and meets the contrast standard (WCAG AA). The light theme badge keeps its white text, which already met the standard (PR #128).
  - In the light theme, the focus ring (the outline around the control you have selected with the keyboard) is darker so it is readable on white (PR #128).

## [1.3.0] - 2026-11-12

This minor release adds a Solo blocks list and guidance for a Bitcoin node that refuses the app, plus wall display, appearance and discovery fixes and security hardening since v1.2.0.

### Added
- **Solo blocks:**
  - A Solo blocks page lists the latest 20 blocks found by solo pools (Solo CK, Public Pool, Braiins Solo, FutureBit Apollo Solo and SoloPool.com), newest first, from mempool.space. A block found by one of your own miners is marked. If outside lookups are off, the page says so. If nothing can be read, it shows an error instead of an empty list. The wall display is unchanged (#98, PR #104).
- **Node refusal guidance:**
  - When discovery finds a Bitcoin node that refuses the app, the app now says why (the login is missing or wrong, this computer is not allowed, or the node did not answer) and what to change. The dashboard node card and the discovery panel show the next step in plain English. The same reason and next step reach agents through the API, the MCP tools and the agent guide. The node login is never shown or logged (#99, PR #103).

### Fixed
- **Wall display:**
  - The Overview panel now fits above the footer, so the page no longer overflows at 1280x720 (PR #100).
  - The wall display says when the Bitcoin price has stopped updating, and the chart's stale notice is larger and easier to read (PR #102).
  - The stale-price notice no longer appears for a price you typed in yourself while settings are still loading (PR #112).
  - On a square screen, the Overview panel now fits the same way as a portrait screen, matching how the page lays out its figures (PR #109).
- **Customize:**
  - Read-only viewers no longer see Customize and "Reset dashboard layout", because only an admin can save a layout. Appearance gives a short reason (PR #101).
  - Appearance changes made with a control token are now kept on this device. Before, the app tried to save them on the server, which refuses anyone but an admin (PR #108).
- **Discovery:**
  - A Bitcoin node you saved by its host name is now recognized as already added when a scan finds it by its IP address. A name that cannot be looked up in time is treated as no match and does not stop the scan (PR #113).
  - A scan now has one limit of 4096 different addresses and 16 ranges in total, and it refuses a larger request with a plain message. Addresses are checked a limited number at a time instead of all at once (PR #114).
- **Security hardening:**
  - Raw miner diagnostics now hide passwords, tokens, keys and logins inside web addresses at any depth. Model, hostname and MAC address are still shown (PR #110).
  - A source address can no longer contain a user name or password. A login saved that way earlier is hidden in the source list and in the config export (PR #111).
  - Replies from miners, pools, explorers and Bitcoin nodes are now read with a size limit. A reply over the limit is refused instead of being read in full (PR #115).

## [1.2.0] - 2026-11-12

This minor release adds wall display and Customize features since v1.1.3. They were developed as separate pull requests and merged together as one change (PR #95).

### Added
- **Wall display:**
  - A visible **Wall display** button in the top bar and in the phone navigation, so the wall display no longer hides in the three-dot menu (#76, PR #84).
  - Large, labelled panel buttons with previous and next controls, plus a lock button that keeps the display on the current panel (#77, PR #85).
  - You can choose the time frame of the big headline on the Odds panel. The 10-minute window is shown as "Next block". Only an admin can change this in Settings (#78, PR #86).
  - The network panel leads with the next halving, followed by the next difficulty change (#79, PR #87).
  - The chart is large and labelled, so it can be read from a distance (#80, PR #88).
  - Panels fill the screen at any size, including portrait. An incomplete last row of miners is centred, and the panels leave room for the controls (#81, PR #86, PR #87, PR #89).
- **Customize:**
  - The Bitcoin and Odds & costs pages have a Customize button, like the Dashboard (#82, PR #90).

## [1.1.3] - 2026-11-11

This patch release collects 32 bug fixes made since v1.1.2.

### Fixed
- **Alerts and blocks:**
  - A rule that fails to evaluate no longer clears its alert state (#18, PR #47).
  - A found block and its event are now saved in one transaction (#20, PR #48).
  - Old blocks are looked up through mempool.space, and found blocks replaced by a chain reorganization are marked as replaced (#38, PR #73).
- **Monitoring and metrics:**
  - A miner keeps being polled after a brief failure that follows a successful read (#19, PR #54).
  - Unknown, disabled and stale miners are reported as not up in metrics (#32, PR #62).
  - Electricity cost shows as unknown when a miner's power is missing (#33, PR #58).
  - Disabled source creation is honored, and healed miners are relocated under the fleet lock (#36, PR #70).
  - Unsaved samples are capped while storage is failing, and the storage problem is reported (#37, PR #65).
  - Miners whose firmware reports a group or all-zero MAC address (for example the Magic Miner BG02) stay online; such a MAC is treated as unknown, and control actions are refused until the miner's identity can be verified (#75, PR #83).
  - A single poll with a mismatched miner identity no longer flips a working miner offline; it counts as one failed poll, and a miner that has really been replaced still goes offline at the normal threshold (#92, PR #93).
- **Data safety and storage:**
  - A database written by a newer version is refused instead of opened (#30, PR #46).
  - Config import now applies fully or not at all (#31, PR #55).
- **Settings, forms and dashboard:**
  - Discovery status recovers after a polling failure (#12, PR #16).
  - The service worker registers even when startup finishes after the page has loaded (#15, PR #17).
  - Pool, tuning and fan forms check the result of the action before reporting success (#21, PR #49).
  - Settings saves run in order, so an older answer cannot overwrite a newer one (#22, PR #50).
  - A late full refresh no longer overwrites newer live updates (#23, PR #53).
  - Bulk Apply is tied to the exact preview that succeeded (#24, PR #52).
  - Superseded Analytics, what-if and Activity responses are ignored (#25, PR #72).
  - Failed loads show an error instead of an empty or all-clear state (#26, PR #71).
  - The service worker only cleans up its own caches and finishes its writes within the event (#39, PR #63).
- **Accessibility:**
  - Collapsed navigation links have names, palette arrow keys follow the order shown, and the range picker stays within its container (#42, PR #69).
  - Time-series charts include a text summary and a data table (#43, PR #66).
  - Dashboard customization has keyboard move controls and inert previews (#44, PR #68).
- **Security hardening:**
  - Passwords are hashed in a bounded worker thread (#35, PR #59).
  - The Bitcoin Core cookie file is tied to its own source's settings and validated (#45, PR #56).
  - CSV export headers stay literal when opened in spreadsheets (#34, PR #61).
  - The Vite development server keeps its Host check on when listening on the LAN (#41, PR #64).
- **Installer and Windows:**
  - The installer refuses an unresolved stop state, and autostart configuration is pinned (#40, PR #67). The hosted Windows check now also upgrades from the published v1.1.2 installer.
- **Release pipeline and CI:**
  - Publishing waits for the full test suite and the Windows smoke test (#27, PR #57).
  - The prerelease channel comes from one parsed tag (#28, PR #51).
  - Publishing workflow actions are pinned to commit SHAs (#29, PR #60).
  - These new gates have not yet run on a real tag.

## [1.1.2] - 2026-10-28

This targeted release repairs storage, miner controls, monitoring, alerts, authentication, dashboard behavior and platform tooling, and includes a rebuilt Windows installer.

### Added
- **Next 10 minutes** block odds: a fixed 600-second probability window (`ten_minutes`) alongside day, month and year estimates. The next network block can arrive at any time.
- A rebuilt native Windows installer for the v1.1.x app. Preserve v0.9.x data; `bsmm migrate-legacy` imports miner connection records while historical telemetry remains in the old installation.

### Fixed
The repair set covers 48 distinct audited defects, grouped below.
- **Storage and controls:** keep concurrent database writes in their own transactions. Reject conflicting miner identities and invalid edits without disturbing the saved device. Queue controls per miner, validate previews, finish pending samples at shutdown and keep removed history from reappearing.
- **Monitoring:** show zero when a miner stops hashing, use fresh fallback sources and refresh device-reported difficulty. Retry incomplete block reads. Calculate history averages from valid samples and use retained rollups for older ranges.
- **Alerts and delivery:** honor device/tag scope, retain critical events and reject invalid thresholds. Preserve notification secrets exactly, report partial email failures and keep credentials out of error logs.
- **Authentication and API:** preserve password protection when unrelated settings fail validation. Check request origins and hosts, segregate imported secrets, enforce streamed-body limits and close streams after token revocation. Correct address validation, capture redaction, credential rotation, null settings and discovery shutdown.
- **Existing notification data:** move recognized old plaintext channel credentials into encrypted storage before opening the store to consumers. Preserve exact values, existing encrypted credentials, keys and channel metadata; roll back and refuse startup if repair cannot safely proceed.
- **Dashboard:** restore sign-in from public viewing and return to login after logout or expiry. Preserve layouts and unsaved edits, show failed data loads honestly, test edited notification drafts and prevent duplicate setup channels. Save notes without reverting a rename and retain local appearance choices.
- **CLI and platform tools:** correct Windows liveness checks and stale PID handling. Change passwords on the intended server, report service-manager failures, escape launchd paths and emit one setup JSON result. Restrict screenshot tooling to demo backends and fix its Playwright project selection.
- **Windows acceptance:** produce old data with pinned v1.1.1 application code, then require installed v1.1.2 first-open migration, preservation and reopen. Cold setup must own its loopback discovery ports. Set isolated build paths at runtime so the workflow passes expression validation; native execution remains a separate release gate.

### Documentation
- A prominent agent setup prompt, mixed-fleet overview, official GitHub artifact installation, legacy-data preservation and firmware/API compatibility limits.
- Running agent guidance now requires confirmation before adoption, explains unattended setup and starts with least-scope monitoring. Public docs clarify outbound traffic, backups and fixed-window odds.

Optional performance work is outside this repair set.

## [1.1.1] - 2026-10-27

### Fixed
- Include the built web UI in the source distribution as well as the wheel, so the default `uv build` path and wheels rebuilt from the source archive retain the dashboard.
- The v1.1.0 release stopped at its missing-UI assertion before publication. Its tag is retained; this packaging fix uses v1.1.1.

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
  - Error handling and verification
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
