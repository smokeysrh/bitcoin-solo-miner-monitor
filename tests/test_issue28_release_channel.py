"""Issue #28: one parse of the release tag decides the canonical version and the release channel.

The release workflow used substring checks, so ``v1.2.0a1`` was published as stable and as ``latest``.
These tests run the real ``scripts/release_version.py`` that the workflows call.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "release_version.py"

STABLE = [("v1.2.0", "1.2.0"), ("v10.20.30", "10.20.30")]
CANONICAL_PRERELEASES = [("v1.2.0a1", "1.2.0a1"), ("v1.2.0b1", "1.2.0b1"), ("v1.2.0rc1", "1.2.0rc1")]
HYPHEN_PRERELEASES = [
    ("v1.2.0-alpha.1", "1.2.0a1"),
    ("v1.2.0-beta.1", "1.2.0b1"),
    ("v1.2.0-rc.1", "1.2.0rc1"),
    ("v1.2.0-rc1", "1.2.0rc1"),
]
UNSUPPORTED = ["v1.2", "1.2.0", "vfoo", "v1.2.0.dev1", "v1.2.0.post1", "v1.2.0-1", "v1.2.0+local", "v1.2.0-"]


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("release_version", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, check=False)


@pytest.mark.parametrize(("tag", "canonical"), STABLE)
def test_stable_tags_are_stable(tag, canonical):
    parsed = load_script().parse_tag(tag)
    assert (parsed.version, parsed.is_prerelease) == (canonical, False)


@pytest.mark.parametrize(("tag", "canonical"), CANONICAL_PRERELEASES + HYPHEN_PRERELEASES)
def test_every_prerelease_spelling_is_prerelease_with_canonical_version(tag, canonical):
    parsed = load_script().parse_tag(tag)
    assert (parsed.version, parsed.is_prerelease) == (canonical, True)


@pytest.mark.parametrize("tag", UNSUPPORTED)
def test_unsupported_tags_are_rejected(tag):
    with pytest.raises(ValueError, match="tag"):
        load_script().parse_tag(tag)


@pytest.mark.parametrize(("tag", "canonical"), STABLE + CANONICAL_PRERELEASES + HYPHEN_PRERELEASES)
def test_cli_writes_github_output_lines(tag, canonical):
    result = run_cli(tag)
    prerelease = "true" if (tag, canonical) not in STABLE else "false"
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"version={canonical}\nis_prerelease={prerelease}\n"


def test_cli_canonical_prints_only_the_version_for_exact_comparison():
    result = run_cli("v1.2.0-rc.1", "--canonical")
    assert result.returncode == 0, result.stderr
    assert result.stdout == "1.2.0rc1\n"


@pytest.mark.parametrize("tag", UNSUPPORTED)
def test_cli_fails_closed_without_output_for_unsupported_tags(tag):
    result = run_cli(tag)
    assert result.returncode != 0
    assert result.stdout == ""
    assert tag in result.stderr
