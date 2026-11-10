"""The hosted Windows run must prove an upgrade from the published v1.1.2 installer (issue #40).

These read the workflow text, like the other workflow checks in test_windows_build.py: the native smoke itself only
runs on hosted Windows, so this pins that it is actually given the previous release's setup.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/windows.yml").read_text()
ASSET = "bsmm-1.1.2-windows-setup.exe"
# From the v1.1.2 release's published SHA256SUMS asset
ASSET_SHA256 = "f971da129f5810d2f399d786774544441bc572aa459e88e3b5b0b1ff04a10f1c"
SMOKE_STEP = "Native disposable lifecycle and installer smoke"
ENV_VARIABLE = "BSMM_PREVIOUS_INSTALLER"
EXISTING_ACTIONS = {"actions/checkout@v4", "actions/setup-node@v4", "astral-sh/setup-uv@v5", "actions/upload-artifact@v4"}


def _steps() -> list[str]:
    return ["      - " + chunk for chunk in WORKFLOW.split("\n      - ")[1:]]


def _step(title: str) -> str:
    matches = [step for step in _steps() if step.startswith(f"      - name: {title}")]
    assert len(matches) == 1, f"expected exactly one step named {title!r}"
    return matches[0]


def _download_step() -> str:
    matches = [step for step in _steps() if "gh release download" in step]
    assert len(matches) == 1, "expected exactly one step that downloads the previous release"
    return matches[0]


def test_previous_release_installer_is_downloaded_before_the_native_smoke():
    download = _download_step()
    assert "gh release download v1.1.2" in download
    assert f"--pattern '{ASSET}'" in download
    assert '--repo "$env:GITHUB_REPOSITORY"' in download
    assert "GH_TOKEN: ${{ github.token }}" in download
    assert WORKFLOW.index(download) < WORKFLOW.index(_step(SMOKE_STEP))


def test_download_fails_closed_and_exports_the_installer_path():
    download = _download_step()
    assert "$LASTEXITCODE -ne 0" in download and "throw" in download
    assert ".Length -le 0" in download  # missing or empty file is an error, not a skipped upgrade check
    assert f"{ENV_VARIABLE}=$installer\" >> $env:GITHUB_ENV" in download
    assert ASSET in download
    # the binary is the exact published asset, not whatever the tag happens to serve later
    assert "Get-FileHash -Algorithm SHA256" in download and ASSET_SHA256 in download


def test_native_smoke_receives_the_downloaded_installer_as_previous_installer():
    smoke = _step(SMOKE_STEP)
    invocation = next(line for line in smoke.splitlines() if "installer/windows/smoke.py" in line)
    assert f'--previous-installer "$env:{ENV_VARIABLE}"' in invocation
    # every argument the candidate smoke already used is still passed
    for argument in ("--exe", "--installer", "--expected-version", "--legacy-source .ci-legacy-v1.1.1"):
        assert argument in invocation
    # the guarded behaviours around the smoke are untouched
    for guard in ("native_port_preflight", "Stop-Service -Name W3SVC", "Start-Service -Name W3SVC", "native_iis_restored"):
        assert guard in smoke


def test_workflow_keeps_its_read_only_unpublished_contract():
    assert "permissions:\n  contents: read\n" in WORKFLOW
    assert "contents: write" not in WORKFLOW and "secrets." not in WORKFLOW
    assert set(re.findall(r"uses: (\S+)", WORKFLOW)) == EXISTING_ACTIONS
    assert not re.search(r"gh release (?!download)|gh (?:api|pr|issue)", WORKFLOW)
