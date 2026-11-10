"""Issue #28 (review round): the release workflows must use the one parsed tag, in the locked environment.

PR CI never runs the tag-only release jobs, so the wiring is guarded here as workflow text, like
``tests/test_windows_build.py``. The channel decision itself is covered by
``test_issue28_release_channel.py``.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
RELEASE = (WORKFLOWS / "release.yml").read_text()
WINDOWS = (WORKFLOWS / "windows.yml").read_text()
PRERELEASE_OUTPUT = "needs.package.outputs.is_prerelease"


def lines_containing(text: str, needle: str) -> list[str]:
    """Non-comment workflow lines that contain ``needle``."""
    stripped = (line.strip() for line in text.splitlines())
    return [line for line in stripped if needle in line and not line.startswith("#")]


def test_no_workflow_derives_the_channel_from_the_tag_text():
    for workflow in sorted(WORKFLOWS.glob("*.yml")):
        assert "contains(github.ref_name" not in workflow.read_text(), workflow.name


def test_github_prerelease_flag_uses_the_parsed_channel():
    flags = [line for line in lines_containing(RELEASE, "prerelease:") if line.startswith("prerelease:")]
    assert len(flags) == 1
    assert PRERELEASE_OUTPUT in flags[0]


def test_docker_stable_aliases_use_the_parsed_channel():
    for needle in ("{{major}}.{{minor}}", "value=latest"):
        tags = lines_containing(RELEASE, needle)
        assert len(tags) == 1, needle
        assert f"enable=${{{{ {PRERELEASE_OUTPUT} != 'true' }}}}" in tags[0], tags[0]


def test_release_version_script_runs_in_the_locked_environment():
    for name, text in (("release.yml", RELEASE), ("windows.yml", WINDOWS)):
        calls = lines_containing(text, "scripts/release_version.py")
        assert calls, name
        for call in calls:
            assert "--no-sync" in call, call
            assert "--with" not in call and "--no-project" not in call, call
        assert "uv sync --frozen" in text[: text.index(calls[0])], name


def test_locked_environment_provides_packaging():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert any(dep.startswith("packaging") for dep in pyproject["project"]["dependencies"])
    assert 'name = "packaging"' in (ROOT / "uv.lock").read_text()
