"""Issue #40 review round: upgrade-compatible installer stop gate and live-server detection.

OS processes are faked and nothing is launched or signalled. Native Windows proof comes from the hosted smoke
(`--previous-installer`), not from these tests.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from installer.windows import smoke
from typer.testing import CliRunner

import bsmm.cli.main as main
from bsmm.cli import lifecycle

ROOT = Path(__file__).resolve().parents[1]
BSMM_ENV = ("BSMM_DATA_DIR", "BSMM_PORT", "BSMM_HOST", "BSMM_OFFLINE", "BSMM_DEMO", "BSMM_AUTH", "BSMM_ADMIN_PASSWORD")


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in BSMM_ENV:
        monkeypatch.delenv(name, raising=False)


def _stop(data: Path, *extra: str):
    return CliRunner().invoke(main.app, ["stop", *extra, "--data-dir", str(data), "--json"])


def _process(pid: int, exe: str, *args: str) -> SimpleNamespace:
    return SimpleNamespace(info={"pid": pid, "exe": exe, "cmdline": [exe, *args]})


def _installed_build_with(monkeypatch: pytest.MonkeyPatch, *processes: SimpleNamespace) -> list[object]:
    """Pretend to be the frozen installed exe, with these other processes on the machine. Returns recorded signals."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(lifecycle.psutil, "process_iter", lambda *a, **k: iter(processes))
    signalled: list[object] = []

    def fake_kill(pid: int, sig: int) -> None:
        if sig != 0:  # signal 0 is psutil's existence probe, not a stop attempt
            signalled.append((pid, sig))

    monkeypatch.setattr(main.os, "kill", fake_kill)
    monkeypatch.setattr(main.subprocess, "run", lambda *args, **kw: signalled.append(args))
    return signalled


FOREGROUND = ("serve", "--port", "8420")


def test_strict_stop_refuses_a_live_server_when_no_state_file_exists(tmp_path, monkeypatch):
    signalled = _installed_build_with(monkeypatch, _process(7001, sys.executable, *FOREGROUND))
    result = _stop(tmp_path, "--strict")
    assert result.exit_code == 1, result.output
    assert signalled == []


def test_strict_stop_refuses_a_live_server_when_the_data_directory_is_missing(tmp_path, monkeypatch):
    signalled = _installed_build_with(monkeypatch, _process(7001, sys.executable, "serve"))
    result = _stop(tmp_path / "never-created", "--strict")
    assert result.exit_code == 1, result.output
    assert signalled == []


def test_strict_stop_refuses_a_scheduled_server_even_with_dead_recorded_state(tmp_path, monkeypatch):
    (tmp_path / "bsmm.pid").write_text("424242")  # legacy file for a process that is gone
    monkeypatch.setattr(lifecycle.psutil, "pid_exists", lambda pid: False)
    signalled = _installed_build_with(monkeypatch, _process(7002, sys.executable, "serve", "--data-dir", "elsewhere"))
    result = _stop(tmp_path, "--strict")
    assert result.exit_code == 1, result.output
    assert (tmp_path / "bsmm.pid").exists() and signalled == []


def test_strict_stop_refuses_when_another_server_runs_beside_the_stopped_instance(tmp_path, monkeypatch):
    (tmp_path / "bsmm.pid").write_text(json.dumps({"token": "fixture"}))
    monkeypatch.setattr(lifecycle, "owned_process",
                        lambda *a: None if (tmp_path / "bsmm.stop").exists() else SimpleNamespace())
    _installed_build_with(monkeypatch, _process(7003, sys.executable, "serve"))
    result = _stop(tmp_path, "--strict")
    assert result.exit_code == 1, result.output


def test_strict_stop_ignores_unrelated_and_own_processes(tmp_path, monkeypatch):
    _installed_build_with(
        monkeypatch,
        _process(7004, str(tmp_path / "other" / "bsmm.exe"), "serve"),     # a different install
        _process(7005, sys.executable, "status"),                           # same exe, not a server
        _process(os.getpid(), sys.executable, "serve"),                     # this very process
        SimpleNamespace(info={"pid": 7006, "exe": None, "cmdline": None}),  # unreadable (other user)
    )
    result = _stop(tmp_path, "--strict")
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["stopped"] is False


def test_strict_stop_does_not_scan_processes_outside_the_installed_build(tmp_path, monkeypatch):
    _installed_build_with(monkeypatch, _process(7001, sys.executable, "serve"))
    monkeypatch.delattr(sys, "frozen")
    result = _stop(tmp_path, "--strict")
    assert result.exit_code == 0, result.output


def test_default_stop_does_not_scan_or_refuse(tmp_path, monkeypatch):
    signalled = _installed_build_with(monkeypatch, _process(7001, sys.executable, "serve"))
    result = _stop(tmp_path)
    assert result.exit_code == 0, result.output
    assert signalled == []


# --- upgrade from a release that has no `stop --strict` -----------------------------------------------------------------------------


def test_installer_falls_back_to_plain_stop_only_when_strict_is_an_unknown_option():
    # Inno code cannot run on Linux; the hosted native upgrade smoke is the behavioural proof. This pins the decision rule.
    code = (ROOT / "installer/windows/bsmm.iss").read_text().split("[Code]", 1)[1].split("function PrepareToInstall", 1)[0]
    strict, plain = code.index("'stop --strict'"), code.index("'stop'")
    assert strict < plain
    between = code[strict:plain]
    assert "Code = 2" in between  # Typer's usage-error exit, what a release without --strict returns
    assert code.count("'stop'") == 1 and "Result and (Code = 0)" in code[plain:]


def test_previous_release_is_installed_and_running_before_the_candidate_replaces_it(monkeypatch, tmp_path):
    events: list[str] = []
    target = tmp_path / "installed app"
    exe = str(target / "bsmm.exe")
    monkeypatch.setattr(smoke.sys, "platform", "win32")
    monkeypatch.setattr(smoke, "check_assets", lambda *a: events.append("assets"))

    def run(command, env, **kwargs):
        if command[0] == "old-release-fixture":
            events.append("install-previous")
            target.mkdir()
            Path(exe).touch()
        elif command[0] == "candidate-fixture":
            assert "start" in events, "candidate must replace a running previous release"
            events.append("install-candidate")
        elif command[0] == str(target / "unins000.exe"):
            events.append("uninstall")
            Path(exe).unlink()
        else:
            pytest.fail(f"Unexpected command {command}")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def cli(command, env, *args):
        assert command == [exe]
        events.append(args[0])
        return {"stopped": True} if args[0] == "stop" else {"running": True, "pid": 1}

    monkeypatch.setattr(smoke, "run", run)
    monkeypatch.setattr(smoke, "cli", cli)
    smoke.previous_release_upgrade(Path("old-release-fixture"), Path("candidate-fixture"), tmp_path, "1.1.3")
    assert events == ["install-previous", "start", "install-candidate", "start", "assets", "stop", "uninstall"]


def test_smoke_cli_wires_the_previous_installer_after_the_main_smoke(monkeypatch, tmp_path):
    monkeypatch.setattr(smoke.tempfile, "tempdir", str(tmp_path))
    calls: list[str] = []
    monkeypatch.setattr(smoke, "smoke", lambda *a: calls.append("smoke") or {"ok": True})
    monkeypatch.setattr(smoke, "refusal_with_live_server", lambda *a: calls.append("refusal"))  # native-only; ordered in test_issue40_native_refusal
    monkeypatch.setattr(smoke, "previous_release_upgrade", lambda *a: calls.append("previous"))
    smoke.main(["--expected-version", "1.1.3", "--legacy-source", str(tmp_path),
                "--installer", str(tmp_path / "new.exe"), "--previous-installer", str(tmp_path / "old.exe")])
    assert calls == ["smoke", "refusal", "previous"]


def test_previous_installer_requires_the_candidate_installer(tmp_path):
    with pytest.raises(SystemExit):
        smoke.main(["--expected-version", "1.1.3", "--legacy-source", str(tmp_path),
                    "--previous-installer", str(tmp_path / "old.exe")])
