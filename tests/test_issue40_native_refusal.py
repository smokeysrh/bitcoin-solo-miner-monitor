"""Issue #40 review round 4: native refusal scenario of the hosted Windows smoke.

A server that `bsmm stop --strict` must refuse (a foreground `serve` of the installed exe, no PID record) is running while
the candidate installer is applied. The smoke must assert the installer exits non-zero, leaves installed files and user
data unchanged, leaves that server answering, and then stop it cooperatively. Processes and the installer are faked here;
the real Windows behaviour is proven only by the hosted native smoke.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from installer.windows import smoke

CANDIDATE = "candidate-fixture"
VERSION = "1.1.3"


class FakeServer:
    """Stands in for the foreground `bsmm.exe serve --managed-token ...` child; only a matching stop file ends it."""

    def __init__(self, argv: list[str], **kwargs: object) -> None:
        self.argv, self.kwargs = argv, kwargs
        self.token = argv[argv.index("--managed-token") + 1]
        self.data = Path(argv[argv.index("--data-dir") + 1])
        self.exited = False
        self.terminated = False
        (self.data / "secret.key").write_text("fixture key")
        (self.data / "bsmm.ready").write_text(self.token)  # what the real managed server announces once it listens

    def poll(self) -> int | None:
        return 0 if self.exited else None

    def wait(self, timeout: float | None = None) -> int:
        stop = self.data / "bsmm.stop"
        if not self.exited and not (stop.exists() and stop.read_text() == self.token):
            raise subprocess.TimeoutExpired(self.argv, timeout or 0)
        self.exited = True
        return 0

    def terminate(self) -> None:
        self.terminated = self.exited = True


class Scenario:
    def __init__(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, installer_exit: int = 1,
                 installer_edit: str | None = None, installer_kills_server: bool = False) -> None:
        self.root = tmp_path / "refusal"
        self.target = self.root / "installed app"
        self.exe = str(self.target / "bsmm.exe")
        self.events: list[str] = []
        self.servers: list[FakeServer] = []
        self.installs = 0
        self.installer_exit, self.installer_edit, self.installer_kills_server = installer_exit, installer_edit, installer_kills_server
        monkeypatch.setattr(smoke.sys, "platform", "win32")
        monkeypatch.setattr(smoke, "port", lambda: 5999)
        monkeypatch.setattr(smoke, "run", self.run)
        monkeypatch.setattr(smoke, "fetch", lambda base, path: b"{}")
        monkeypatch.setattr(smoke, "check_assets", lambda *a: self.events.append("assets"))
        monkeypatch.setattr(smoke, "credentials", lambda data: ("password hash", b"key"))
        monkeypatch.setattr(smoke.subprocess, "Popen", self.popen)

    def popen(self, argv: list[str], **kwargs: object) -> FakeServer:
        assert argv[0] == self.exe and argv[1] == "serve", "the server must be a foreground serve of the installed exe"
        assert "start" not in argv, "a `start`ed server has a PID record and would not exercise the unrecorded path"
        self.events.append("serve")
        self.servers.append(FakeServer(argv, **kwargs))
        return self.servers[0]

    def running(self) -> bool:
        return bool(self.servers) and self.servers[0].poll() is None

    def run(self, command: list[str], env: dict[str, str], *, success: bool = True) -> SimpleNamespace:
        code = 0
        if command[0] == CANDIDATE and self.installs == 0:
            self.installs += 1
            self.events.append("install")
            (self.target / "_internal").mkdir(parents=True)
            Path(self.exe).write_bytes(b"exe")
            (self.target / "_internal" / "lib.bin").write_bytes(b"lib")
            (self.target / "unins000.exe").write_bytes(b"uninstaller")
        elif command[0] == CANDIDATE:
            assert self.running(), "the candidate installer must meet a running server"
            self.events.append("installer")
            code = self.installer_exit
            if self.installer_edit == "program":
                Path(self.exe).write_bytes(b"replaced")
            elif self.installer_edit == "data":
                (self.root / "data" / "preserve.txt").write_text("changed")
            if self.installer_kills_server:
                self.servers[0].exited = True
        elif command[:2] == [self.exe, "password"]:
            pass  # offline-local credential seeding in the owned data directory
        elif command == [self.exe, "stop", "--strict"]:
            code = 1 if self.running() else 0
            self.events.append("strict-stop-refused" if code else "strict-stop-ok")
        elif command == [self.exe, "stop"]:
            self.events.append("cleanup-stop")
        elif command[0] == str(self.target / "unins000.exe"):
            self.events.append("uninstall")
            Path(self.exe).unlink()
        else:
            pytest.fail(f"Unexpected command {command}")
        if success and code != 0:
            raise RuntimeError(f"smoke command failed (exit {code}); captured output withheld")
        return SimpleNamespace(returncode=code, stdout="", stderr="")

    def call(self) -> None:
        smoke.refusal_with_live_server(Path(CANDIDATE), self.root, VERSION)


def test_refused_upgrade_leaves_files_data_and_the_unrecorded_server_untouched(monkeypatch, tmp_path, capsys):
    scenario = Scenario(monkeypatch, tmp_path)
    scenario.call()
    assert scenario.events == ["install", "serve", "strict-stop-refused", "installer", "assets", "strict-stop-ok", "uninstall"]
    server = scenario.servers[0]
    assert server.exited and not server.terminated, "the server must end through its own stop file, not be killed"
    assert not (scenario.root / "data" / "bsmm.pid").exists()
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1]) == {"installer_refuses_live_server": True}


def test_server_is_owned_offline_loopback_on_the_owned_port(monkeypatch, tmp_path):
    scenario = Scenario(monkeypatch, tmp_path)
    scenario.call()
    argv, data = scenario.servers[0].argv, scenario.root / "data"
    assert argv[argv.index("--port") + 1] == "5999" and argv[argv.index("--host") + 1] == "127.0.0.1"
    assert argv[argv.index("--data-dir") + 1] == str(data) and "--offline" in argv
    assert scenario.servers[0].kwargs["stdout"] is subprocess.DEVNULL and scenario.servers[0].kwargs["stderr"] is subprocess.DEVNULL


def test_installer_that_exits_zero_with_a_live_server_fails_the_smoke_and_cleans_up(monkeypatch, tmp_path):
    scenario = Scenario(monkeypatch, tmp_path, installer_exit=0)
    with pytest.raises(AssertionError):
        scenario.call()
    assert scenario.servers[0].poll() is not None, "a failed scenario must not leak its server"
    assert "strict-stop-ok" not in scenario.events


@pytest.mark.parametrize("edit", ["program", "data"])
def test_changed_program_files_or_user_data_fail_the_smoke(monkeypatch, tmp_path, edit):
    scenario = Scenario(monkeypatch, tmp_path, installer_edit=edit)
    with pytest.raises(AssertionError):
        scenario.call()
    assert scenario.servers[0].poll() is not None, "a failed scenario must not leak its server"


def test_a_server_that_died_during_the_refused_install_fails_the_smoke(monkeypatch, tmp_path):
    scenario = Scenario(monkeypatch, tmp_path, installer_kills_server=True)
    with pytest.raises(AssertionError):
        scenario.call()
    assert "strict-stop-ok" not in scenario.events


def test_the_refusal_scenario_is_native_windows_only(monkeypatch, tmp_path):
    scenario = Scenario(monkeypatch, tmp_path)
    monkeypatch.setattr(smoke.sys, "platform", "linux")
    with pytest.raises(RuntimeError):
        scenario.call()
    assert scenario.events == []


def test_smoke_cli_runs_the_refusal_scenario_between_the_main_smoke_and_the_previous_release(monkeypatch, tmp_path):
    monkeypatch.setattr(smoke.tempfile, "tempdir", str(tmp_path))
    calls: list[object] = []
    monkeypatch.setattr(smoke, "smoke", lambda *a: calls.append("smoke") or {"ok": True})
    monkeypatch.setattr(smoke, "refusal_with_live_server", lambda *a: calls.append(("refusal", a[0].name, a[2])))
    monkeypatch.setattr(smoke, "previous_release_upgrade", lambda *a: calls.append("previous"))
    smoke.main(["--expected-version", VERSION, "--legacy-source", str(tmp_path),
                "--installer", str(tmp_path / "new.exe"), "--previous-installer", str(tmp_path / "old.exe")])
    assert calls == ["smoke", ("refusal", "new.exe", VERSION), "previous"]


def test_smoke_cli_runs_the_refusal_scenario_for_the_installer_alone_and_never_without_one(monkeypatch, tmp_path):
    monkeypatch.setattr(smoke.tempfile, "tempdir", str(tmp_path))
    calls: list[str] = []
    monkeypatch.setattr(smoke, "smoke", lambda *a: calls.append("smoke") or {"ok": True})
    monkeypatch.setattr(smoke, "refusal_with_live_server", lambda *a: calls.append("refusal"))
    smoke.main(["--expected-version", VERSION, "--legacy-source", str(tmp_path), "--installer", str(tmp_path / "new.exe")])
    assert calls == ["smoke", "refusal"]
    calls.clear()
    smoke.main(["--expected-version", VERSION, "--legacy-source", str(tmp_path)])
    assert calls == ["smoke"]
