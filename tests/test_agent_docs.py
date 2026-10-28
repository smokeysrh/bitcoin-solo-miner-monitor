"""The documents agents read must stay true: the tool list matches the real MCP server, and the
llms.txt in the repository root is exactly what the generator produces."""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

from bsmm import __version__
from bsmm.agent_docs import MCP_TOOLS, agent_guide, llms_txt
from bsmm.mcp_server import build_server

ROOT = Path(__file__).resolve().parent.parent


class _NoBackend:
    async def call(self, *a: object, **k: object) -> dict[str, object]:
        return {}


async def test_the_documented_mcp_tools_are_exactly_the_registered_ones():
    registered = [t.name for t in await build_server(_NoBackend()).list_tools()]
    assert registered == MCP_TOOLS


def test_the_guide_and_llms_txt_mention_the_same_setup_steps():
    guide = agent_guide("http://x:8420")
    text = llms_txt("http://x:8420")
    for step in guide["setup_recipe"]:
        assert step["request"]["path"] in text
    assert guide["mcp"]["tools"] == MCP_TOOLS
    for note in guide["setup_preflight"]:
        assert note in text
    for note in guide["safety"]:
        assert note in text


def test_monitoring_defaults_to_read_and_adoption_requires_confirmation():
    guide = agent_guide("http://x:8420")
    assert guide["auth"]["create_token_on_server"].endswith("--scope read")
    adoption = next(s for s in guide["setup_recipe"] if s["request"]["path"].endswith("/adopt"))
    assert "wait for confirmation" in adoption["notes"]
    assert "keys" in adoption["notes"]
    unattended = next(s for s in guide["setup_preflight"] if "setup --yes" in s)
    assert "scans again" in unattended and "skips the password prompt" in unattended
    assert "admin token" in unattended


def test_documented_and_web_versions_match_the_python_version():
    package = json.loads((ROOT / "web" / "package.json").read_text())
    lock = json.loads((ROOT / "web" / "package-lock.json").read_text())
    assert package["version"] == lock["version"] == lock["packages"][""]["version"] == __version__
    assert agent_guide("http://x:8420")["version"] == __version__
    assert f"Version {__version__}." in llms_txt()


def test_the_root_llms_txt_is_up_to_date(monkeypatch):
    # Reuse pytest's source imports so this check also works without installing the app.
    generator = ROOT / "scripts" / "gen_llms_txt.py"
    monkeypatch.setattr(sys, "argv", [str(generator), "--check"])
    assert runpy.run_path(str(generator))["main"]() == 0


def test_every_cli_command_the_agent_docs_mention_exists():
    from typer.main import get_command

    from bsmm.cli.main import app

    commands = set(get_command(app).commands)  # type: ignore[attr-defined]
    for text in ((ROOT / "AGENTS.md").read_text(), (ROOT / "skills" / "solo-miner-monitor" / "SKILL.md").read_text()):
        for word in ("status", "list", "odds", "doctor", "token", "mcp", "demo", "start", "agent-guide"):
            if f"bsmm {word}" in text:
                assert word in commands, f"docs mention `bsmm {word}` but the CLI has no such command"
