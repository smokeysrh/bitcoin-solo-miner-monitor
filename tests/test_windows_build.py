"""Build-source checks complement, but never replace, native Windows smoke."""
import ast
from pathlib import Path

import pytest
from installer.windows.build import package_version, version_resource

from bsmm import __version__

ROOT = Path(__file__).resolve().parents[1]


def test_windows_resource_uses_canonical_version():
    assert package_version() == __version__
    resource = version_resource(__version__)
    ast.parse(resource)
    assert f"StringStruct('ProductVersion', '{__version__}')" in resource
    assert "OriginalFilename', 'bsmm.exe'" in resource
    with pytest.raises(ValueError):
        version_resource("invalid")


def test_windows_installer_preserves_data_and_uses_current_entrypoint():
    text = (ROOT / "installer/windows/bsmm.iss").read_text()
    assert "PrivilegesRequired=lowest" in text
    assert "CloseApplications=no" in text
    assert "[UninstallDelete]" not in text.replace("; Inno removes only the files it installed. No wildcard [UninstallDelete] section.", "")
    assert "StopExisting()" in text and "(Code = 0)" in text
    assert "taskkill" not in text and "run.py" not in text and "python.exe" not in text
    assert 'Parameters: "start --open"' in text and 'Parameters: "stop"' in text


def test_windows_release_waits_for_native_smoke():
    text = (ROOT / ".github/workflows/windows.yml").read_text()
    assert "installer/windows/smoke.py" in text and "--expected-version" in text
    assert text.index("installer/windows/smoke.py") < text.index("actions/upload-artifact")
    release = (ROOT / ".github/workflows/release.yml").read_text()
    assert "needs: [package, windows]" in release and "name: windows-dist" in release


def test_windows_build_paths_use_runtime_environment_before_tools():
    text = (ROOT / ".github/workflows/windows.yml").read_text()
    job_environment, steps = text.split("    steps:\n", 1)
    assert "runner.temp" not in job_environment
    setup = steps.split("      - uses: actions/checkout@v4", 1)[0]
    paths = {
        "UV_PROJECT_ENVIRONMENT": "bsmm-build-venv",
        "UV_CACHE_DIR": "bsmm-cache/uv",
        "PYINSTALLER_CONFIG_DIR": "bsmm-cache/pyinstaller",
        "PLAYWRIGHT_BROWSERS_PATH": "bsmm-cache/playwright",
    }
    for key, suffix in paths.items():
        assert f'"{key}=$env:RUNNER_TEMP/{suffix}" >> $env:GITHUB_ENV' in setup
