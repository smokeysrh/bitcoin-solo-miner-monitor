# Contributing

Thanks for helping. The short version:

1. Read **Part 2 of [`AGENTS.md`](AGENTS.md)**. It has the layout, commands and conventions, and it's the same for people and AI agents.
2. `uv sync --extra dev`, then `bsmm serve --demo --port 8421` and `cd web && npm ci && BSMM_DEV_API=http://127.0.0.1:8421 npm run dev`. The demo has a simulated fleet, so you never need real hardware.
3. Before you open a PR: `ruff check src tests`, `mypy`, `pytest`, and for UI changes `npm run typecheck && npm test && npm run build`.

## What's most useful

- **New miner support.** Run the read-only capture described in AGENTS.md, add a sanitised fixture, extend the driver and the catalog. Please say in the PR whether you tested on the real device.
- **Bug reports with `bsmm doctor` output**. Review it for private hosts, paths and addresses before sharing.
- Translations and plainer wording. Newcomers are the audience.

Label physical hardware checks, recorded replies and simulator coverage by evidence type. Note the firmware version for a hardware check; API-family support varies across firmware and devices. Keep the canonical identification tables in [docs/miner-identification.md](docs/miner-identification.md).

## Documentation and versions

Edit `src/bsmm/agent_docs.py` for the served text and JSON agent guide, then run `python scripts/gen_llms_txt.py` and `python scripts/gen_llms_txt.py --check`. Run `tests/test_agent_docs.py` and the relevant CLI tests when changing setup examples. Use the official GitHub release wheel or platform installer in user instructions; see [docs/PACKAGING.md](docs/PACKAGING.md) for versions and release checks.

## Ground rules

- Never write to a real miner from a test.
- Don't add telemetry. Document outbound requests and give users control over them. Existing traffic includes miners, configured node/pool sources, enabled public data/update services and chosen alert destinations. `BSMM_OFFLINE=1` disables automatic public lookups; configured sources and alerts still make requests.
- Keep secrets write-only.
- Add a test that fails without your fix.
- Use disposable demo data for screenshots and browser tests. Keep private fleet data, credentials and wallet addresses out of fixtures and reports.

By contributing you agree your work is released under the MIT license.
