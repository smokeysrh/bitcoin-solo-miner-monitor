"""Issue #40: an unverified stop is not a safe shutdown, and autostart keeps the effective configuration.

OS processes and service managers are faked; native smoke covers real children. Nothing is launched or signalled.
"""

from __future__ import annotations

import json
import os
import plistlib
import shlex
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import psutil
import pytest
from typer.testing import CliRunner

import bsmm.cli.main as main
from bsmm.cli import lifecycle
from bsmm.config import DEFAULT_HOST, DEFAULT_PORT

BSMM_ENV = (
    "BSMM_DATA_DIR", "BSMM_PORT", "BSMM_HOST", "BSMM_OFFLINE", "BSMM_DEMO", "BSMM_AUTH",
    "BSMM_ADMIN_PASSWORD", "BSMM_URL", "BSMM_TOKEN",
)


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in BSMM_ENV:
        monkeypatch.delenv(name, raising=False)


def _record(data: Path, **override: object) -> dict[str, object]:
    argv = [sys.executable, "-m", "bsmm", "serve", "--data-dir", str(data.resolve()), "--managed-token", "fixture"]
    record: dict[str, object] = {"pid": 424242, "created": 123.0, "exe": sys.executable, "argv": argv,
                                 "data": str(data.resolve()), "token": "fixture", "port": 12345}
    record.update(override)
    return record


def _stop(data: Path, *extra: str):
    return CliRunner().invoke(main.app, ["stop", *extra, "--data-dir", str(data), "--json"])


def _forbid_signals(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    calls: list[object] = []

    def fake_kill(pid: int, sig: int) -> None:
        # Signal 0 is the POSIX existence probe psutil.pid_exists uses; it delivers nothing, so it is not a stop attempt.
        if sig != 0:
            calls.append((pid, sig))

    monkeypatch.setattr(main.os, "kill", fake_kill)
    monkeypatch.setattr(main.subprocess, "run", lambda *args, **kw: calls.append(args))
    return calls


# --- strict stop: only a positive stop or positive absence is a safe shutdown -----------------------------------------------------


def test_strict_stop_accepts_no_recorded_instance(tmp_path):
    result = _stop(tmp_path, "--strict")
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["stopped"] is False


def test_strict_stop_accepts_a_missing_data_directory(tmp_path):
    result = _stop(tmp_path / "never-created", "--strict")
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["stopped"] is False


def test_strict_stop_accepts_a_recorded_process_that_no_longer_exists(tmp_path, monkeypatch):
    (tmp_path / "bsmm.pid").write_text(json.dumps(_record(tmp_path)))

    def gone(pid: int) -> None:
        raise psutil.NoSuchProcess(pid)

    monkeypatch.setattr(lifecycle.psutil, "Process", gone)
    monkeypatch.setattr(lifecycle.psutil, "pid_exists", lambda pid: False)
    signalled = _forbid_signals(monkeypatch)
    result = _stop(tmp_path, "--strict")
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["stopped"] is False
    assert not (tmp_path / "bsmm.pid").exists() and signalled == []


def test_strict_stop_accepts_a_legacy_pid_file_for_a_dead_process(tmp_path, monkeypatch):
    (tmp_path / "bsmm.pid").write_text("424242")
    monkeypatch.setattr(lifecycle.psutil, "pid_exists", lambda pid: False)
    result = _stop(tmp_path, "--strict")
    assert result.exit_code == 0, result.output
    assert not (tmp_path / "bsmm.pid").exists()


def test_strict_stop_accepts_a_pid_reused_by_a_different_process(tmp_path, monkeypatch):
    (tmp_path / "bsmm.pid").write_text(json.dumps(_record(tmp_path)))
    other = SimpleNamespace(create_time=lambda: 999.0)
    monkeypatch.setattr(lifecycle.psutil, "pid_exists", lambda pid: True)
    monkeypatch.setattr(lifecycle.psutil, "Process", lambda pid: other)
    result = _stop(tmp_path, "--strict")
    assert result.exit_code == 0, result.output
    assert not (tmp_path / "bsmm.pid").exists()


def test_strict_stop_refuses_a_legacy_pid_file_for_a_live_process(tmp_path, monkeypatch):
    (tmp_path / "bsmm.pid").write_text(str(os.getpid()))
    signalled = _forbid_signals(monkeypatch)
    result = _stop(tmp_path, "--strict")
    assert result.exit_code == 1, result.output
    assert (tmp_path / "bsmm.pid").read_text() == str(os.getpid())
    assert signalled == []


def test_strict_stop_refuses_a_live_process_whose_identity_does_not_match(tmp_path, monkeypatch):
    (tmp_path / "bsmm.pid").write_text(json.dumps(_record(tmp_path, token="someone-else")))
    live = SimpleNamespace(create_time=lambda: 123.0, exe=lambda: sys.executable, cmdline=lambda: [],
                           is_running=lambda: True, status=lambda: "running")
    monkeypatch.setattr(lifecycle.psutil, "pid_exists", lambda pid: True)
    monkeypatch.setattr(lifecycle.psutil, "Process", lambda pid: live)
    signalled = _forbid_signals(monkeypatch)
    result = _stop(tmp_path, "--strict")
    assert result.exit_code == 1, result.output
    assert (tmp_path / "bsmm.pid").exists() and signalled == []


def test_strict_stop_refuses_a_malformed_record(tmp_path, monkeypatch):
    (tmp_path / "bsmm.pid").write_text("{not json")
    signalled = _forbid_signals(monkeypatch)
    result = _stop(tmp_path, "--strict")
    assert result.exit_code == 1, result.output
    assert (tmp_path / "bsmm.pid").read_text() == "{not json" and signalled == []


def test_strict_stop_still_stops_an_owned_instance(tmp_path, monkeypatch):
    (tmp_path / "bsmm.pid").write_text(json.dumps({"token": "fixture"}))
    monkeypatch.setattr(lifecycle, "owned_process",
                        lambda *a: None if (tmp_path / "bsmm.stop").exists() else SimpleNamespace())
    result = _stop(tmp_path, "--strict")
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {"stopped": True}
    assert not (tmp_path / "bsmm.pid").exists()


def test_default_stop_keeps_removing_unverified_state(tmp_path, monkeypatch):
    # The documented non-strict behaviour (and the native smoke's forged-state check) must not change.
    (tmp_path / "bsmm.pid").write_text(str(os.getpid()))
    signalled = _forbid_signals(monkeypatch)
    result = _stop(tmp_path)
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["stopped"] is False
    assert not (tmp_path / "bsmm.pid").exists() and signalled == []


# --- autostart definitions carry the effective, resolved configuration ------------------------------------------------------------


def _install_argv(platform: str, home: Path, monkeypatch: pytest.MonkeyPatch, *options: str) -> list[str]:
    """Apply `bsmm service install` with the platform and its manager faked; return the definition's command line."""
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setattr("shutil.which", lambda *_a, **_k: None)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    commands: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        commands.append([str(c) for c in cmd])
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = CliRunner().invoke(main.app, ["service", "install", "--apply", *options])
    assert result.exit_code == 0, result.output
    if platform == "linux":
        text = (home / ".config" / "systemd" / "user" / "bsmm.service").read_text()
        line = next(line for line in text.splitlines() if line.startswith("ExecStart="))
        return shlex.split(line[len("ExecStart="):])
    if platform == "darwin":
        plist = home / "Library" / "LaunchAgents" / "com.github.smokeysrh.bsmm.plist"
        return list(plistlib.loads(plist.read_bytes())["ProgramArguments"])
    [create] = commands
    return shlex.split(create[create.index("/TR") + 1])


def _option(argv: list[str], name: str) -> str | None:
    return argv[argv.index(name) + 1] if name in argv else None


@pytest.mark.parametrize("platform", ["linux", "darwin", "win32"])
def test_autostart_captures_environment_configuration(tmp_path, monkeypatch, platform):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BSMM_DATA_DIR", "custom-data")
    monkeypatch.setenv("BSMM_PORT", "8555")
    monkeypatch.setenv("BSMM_HOST", "127.0.0.1")
    monkeypatch.setenv("BSMM_OFFLINE", "1")
    monkeypatch.setenv("BSMM_ADMIN_PASSWORD", "must-never-be-written")
    argv = _install_argv(platform, tmp_path / "home", monkeypatch)
    assert _option(argv, "--port") == "8555"
    assert _option(argv, "--host") == "127.0.0.1"
    assert "--offline" in argv
    assert _option(argv, "--data-dir") == str((tmp_path / "custom-data").resolve())
    assert "must-never-be-written" not in " ".join(argv)


@pytest.mark.parametrize("platform", ["linux", "darwin", "win32"])
def test_autostart_pins_absolute_defaults_when_nothing_is_configured(tmp_path, monkeypatch, platform):
    argv = _install_argv(platform, tmp_path / "home", monkeypatch)
    assert _option(argv, "--port") == str(DEFAULT_PORT)
    assert _option(argv, "--host") == DEFAULT_HOST
    assert "--offline" not in argv
    data_dir = _option(argv, "--data-dir")
    assert data_dir is not None and Path(data_dir).is_absolute()


def test_autostart_explicit_options_win_over_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("BSMM_PORT", "8555")
    argv = _install_argv("linux", tmp_path / "home", monkeypatch,
                         "--port", "9001", "--data-dir", str(tmp_path / "chosen"))
    assert _option(argv, "--port") == "9001"
    assert _option(argv, "--data-dir") == str((tmp_path / "chosen").resolve())
