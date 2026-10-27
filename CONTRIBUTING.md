# Contributing

Thanks for helping. The short version:

1. Read **Part 2 of [`AGENTS.md`](AGENTS.md)**. It has the layout, commands and conventions, and it's the same for people and AI agents.
2. `uv sync --extra dev`, then `bsmm serve --demo --port 8421` and `cd web && npm ci && BSMM_DEV_API=http://127.0.0.1:8421 npm run dev`. The demo has a simulated fleet, so you never need real hardware.
3. Before you open a PR: `ruff check src tests`, `mypy`, `pytest`, and for UI changes `npm run typecheck && npm test && npm run build`.

## What's most useful

- **New miner support.** Run the read-only capture described in AGENTS.md, add a sanitised fixture, extend the driver and the catalog. Please say in the PR whether you tested on the real device.
- **Bug reports with `bsmm doctor` output**.
- Translations and plainer wording. Newcomers are the audience.

## Ground rules

- Never write to a real miner from a test.
- Don't add telemetry or anything that sends data off the user's network without a visible setting.
- Keep secrets write-only.
- Add a test that fails without your fix.

By contributing you agree your work is released under the MIT license.
