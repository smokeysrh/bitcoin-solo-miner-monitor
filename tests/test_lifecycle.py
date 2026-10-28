"""Background lifecycle uses fake OS processes; native smoke exercises real children."""
import json
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

import bsmm.cli.main as main


@pytest.mark.parametrize("platform", ["linux", "darwin", "win32"])
@pytest.mark.parametrize("mismatch", [None, "created", "exe", "argv", "data", "token", "port"])
def test_ops01_ops02_identity_bound_repeated_start_and_stop(tmp_path, monkeypatch, platform, mismatch):
    from bsmm.cli import lifecycle

    argv = [main.sys.executable, "-m", "bsmm", "serve", "--data-dir", str(tmp_path.resolve()), "--managed-token", "fixture"]
    record = {"pid": 424242, "created": 123.0, "exe": main.sys.executable, "argv": argv,
              "data": str(tmp_path.resolve()), "token": "fixture", "port": 12345}
    if mismatch:
        record[mismatch] = "mismatched"
    (tmp_path / "bsmm.pid").write_text(json.dumps(record))
    proc = SimpleNamespace(create_time=lambda: 123.0, exe=lambda: main.sys.executable,
                           cmdline=lambda: argv, is_running=lambda: not (tmp_path / "bsmm.stop").exists(), status=lambda: "running")
    monkeypatch.setattr(lifecycle.psutil, "Process", lambda pid: proc)
    # Query is the same psutil interface on each platform. Fake the Windows
    # lock API on Linux; native Windows CI exercises the real implementation.
    monkeypatch.setattr(lifecycle, "sys", SimpleNamespace(platform=platform, executable=main.sys.executable))
    if platform == "win32":
        monkeypatch.setitem(main.sys.modules, "msvcrt", SimpleNamespace(LK_NBLCK=1, LK_UNLCK=0, locking=lambda *a: None))
    signalled = []
    monkeypatch.setattr(main.os, "kill", lambda *args: signalled.append(args))
    monkeypatch.setattr(main.subprocess, "Popen", lambda *args, **kw: pytest.fail("must not launch"))
    if mismatch:
        result = CliRunner().invoke(main.app, ["stop", "--data-dir", str(tmp_path), "--json"])
        assert json.loads(result.stdout)["stopped"] is False
    else:
        started = CliRunner().invoke(main.app, ["start", "--data-dir", str(tmp_path), "--json"])
        assert json.loads(started.stdout)["pid"] == 424242
        assert json.loads(started.stdout)["already"] is True
        result = CliRunner().invoke(main.app, ["stop", "--data-dir", str(tmp_path), "--json"])
        assert json.loads(result.stdout)["stopped"] is True
    assert signalled == [] and not (tmp_path / "bsmm.pid").exists()


def test_ops02_concurrent_start_stop_refuse_while_lock_held(tmp_path):
    from bsmm.cli import lifecycle

    (tmp_path / "bsmm.pid").write_text("fixture")
    with lifecycle.locked(tmp_path):
        for command in ("start", "stop"):
            result = CliRunner().invoke(main.app, [command, "--data-dir", str(tmp_path)])
            assert result.exit_code != 0 and "in progress" in result.output
            assert (tmp_path / "bsmm.pid").read_text() == "fixture"
        (tmp_path / "bsmm.pid").unlink()
        result = CliRunner().invoke(main.app, ["stop", "--data-dir", str(tmp_path)])
        assert result.exit_code != 0 and "in progress" in result.output


def test_ops02_interrupted_start_cleans_its_child(tmp_path, monkeypatch):
    from bsmm.cli import lifecycle

    state = {"alive": True}
    proc = SimpleNamespace(pid=424243, poll=lambda: None if state["alive"] else 0,
                           wait=lambda **kw: state.update(alive=False))
    monkeypatch.setattr(main.subprocess, "Popen", lambda *args, **kw: proc)
    monkeypatch.setattr(lifecycle, "save_process", lambda *args: (tmp_path / "bsmm.pid").write_text("fixture"))
    def interrupt(*args):
        raise KeyboardInterrupt
    monkeypatch.setattr(lifecycle, "ready", interrupt)
    result = CliRunner().invoke(main.app, ["start", "--data-dir", str(tmp_path)])
    assert result.exit_code != 0
    assert not state["alive"] and not (tmp_path / "bsmm.pid").exists()


def test_ops02_stop_timeout_retains_identity(tmp_path, monkeypatch):
    from bsmm.cli import lifecycle

    (tmp_path / "bsmm.pid").write_text(json.dumps({"token": "fixture"}))
    monkeypatch.setattr(lifecycle, "owned_process", lambda *a: object())
    monkeypatch.setattr(lifecycle, "STOP_SECONDS", 0)
    result = CliRunner().invoke(main.app, ["stop", "--data-dir", str(tmp_path)])
    assert result.exit_code != 0 and "retained" in result.output
    assert (tmp_path / "bsmm.pid").exists()


def test_ops01_liveness_never_uses_windows_kill(monkeypatch):
    calls = []
    monkeypatch.setattr(main.os, "kill", lambda *args: calls.append(args))
    # The existing process is this test; query only, no actual signal ever sent.
    assert main._pid_alive(main.os.getpid())
    assert calls == []


def test_ops02_stale_legacy_pid_never_signals(tmp_path, monkeypatch):
    calls = []
    (tmp_path / "bsmm.pid").write_text("424242")
    monkeypatch.setattr(main.os, "kill", lambda *args: calls.append(args))
    monkeypatch.setattr(main.subprocess, "run", lambda *args, **kw: calls.append(args))
    result = CliRunner().invoke(main.app, ["stop", "--data-dir", str(tmp_path), "--json"])
    assert calls == []
    assert json.loads(result.stdout)["stopped"] is False
    assert not (tmp_path / "bsmm.pid").exists()


def test_ops02_start_refuses_unverified_live_pid(tmp_path, monkeypatch):
    (tmp_path / "bsmm.pid").write_text(str(main.os.getpid()))
    started = []
    monkeypatch.setattr(main.subprocess, "Popen", lambda *a, **kw: started.append(a))
    result = CliRunner().invoke(main.app, ["start", "--data-dir", str(tmp_path), "--json"])
    assert result.exit_code != 0
    assert started == []
    assert "already" not in result.stdout


def test_ops02_failed_start_removes_pid(tmp_path, monkeypatch):
    proc = SimpleNamespace(pid=424243, poll=lambda: 1, wait=lambda **kw: 1)
    monkeypatch.setattr(main.subprocess, "Popen", lambda *a, **kw: proc)
    monkeypatch.setattr(main.Api, "is_up", lambda self: False)
    if hasattr(main, "lifecycle"):
        monkeypatch.setattr(main.lifecycle, "save_process", lambda *a: (tmp_path / "bsmm.pid").write_text("fixture"))
    result = CliRunner().invoke(main.app, ["start", "--data-dir", str(tmp_path), "--json"])
    assert result.exit_code != 0
    assert not (tmp_path / "bsmm.pid").exists()
