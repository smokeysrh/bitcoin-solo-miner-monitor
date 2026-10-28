"""Finite acceptance-harness regressions; not native Windows proof."""
import copy
import json
import socket
import subprocess
from pathlib import Path

import pytest
from installer.windows import legacy_seed, smoke

ROOT = Path(__file__).resolve().parents[1]


def test_workflow_pins_separate_old_source_and_requires_it():
    workflow = (ROOT / ".github/workflows/windows.yml").read_text()
    assert f"ref: {legacy_seed.LEGACY_COMMIT}" in workflow
    assert "path: .ci-legacy-v1.1.1" in workflow
    assert "--legacy-source .ci-legacy-v1.1.1" in workflow
    assert smoke.LEGACY_COMMIT == legacy_seed.LEGACY_COMMIT
    assert workflow.index(f"ref: {legacy_seed.LEGACY_COMMIT}") < workflow.index("installer/windows/smoke.py")


def test_discovery_fixture_covers_every_real_sweep_port():
    from bsmm.engine.discovery import SWEEP_PORTS
    assert smoke.DISCOVERY_PORTS == SWEEP_PORTS


def test_discovery_fixture_refuses_busy_port_before_setup(monkeypatch):
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        monkeypatch.setattr(smoke, "DISCOVERY_PORTS", (busy.getsockname()[1],))
        with pytest.raises(RuntimeError, match="setup not run"), smoke.owned_discovery_ports():
            pytest.fail("Busy fixture must not be admitted")


def test_discovery_fixture_owns_ports_without_listening(monkeypatch):
    chosen = smoke.port()
    monkeypatch.setattr(smoke, "DISCOVERY_PORTS", (chosen,))
    with smoke.owned_discovery_ports():
        with socket.socket() as contender, pytest.raises(OSError):
            contender.bind(("127.0.0.1", chosen))
        with socket.socket() as client:
            client.settimeout(1)
            assert client.connect_ex(("127.0.0.1", chosen)) != 0
    with socket.socket() as released:
        released.bind(("127.0.0.1", chosen))


def test_child_environment_drops_inherited_remote_secret_and_demo(monkeypatch, tmp_path):
    for key in ("BSMM_URL", "BSMM_TOKEN", "BSMM_SECRET_KEY", "BSMM_ADMIN_PASSWORD", "BSMM_DEMO", "HTTPS_PROXY"):
        monkeypatch.setenv(key, "must-not-propagate")
    env = smoke.isolated_env(tmp_path, tmp_path / "data")
    for key in ("BSMM_URL", "BSMM_TOKEN", "BSMM_SECRET_KEY", "BSMM_ADMIN_PASSWORD", "BSMM_DEMO", "HTTPS_PROXY"):
        assert key not in env
    for key in ("HOME", "USERPROFILE", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME", "TMPDIR"):
        assert Path(env[key]).is_relative_to(tmp_path)
    assert env["BSMM_HOST"] == "127.0.0.1"
    assert env["BSMM_OFFLINE"] == env["BSMM_NO_UPDATE_CHECK"] == "1"


@pytest.mark.parametrize("output", ['noise\n{"token":"private"}', '{"token":"private"}\n{}', '[]'])
def test_json_rejects_noise_or_multiple_documents_without_disclosure(monkeypatch, output):
    monkeypatch.setattr(smoke, "run", lambda *args, **kwargs: subprocess.CompletedProcess([], 0, output, ""))
    with pytest.raises(RuntimeError) as caught:
        smoke.cli(["fixture"], {}, "setup")
    assert "private" not in str(caught.value)


def test_command_failure_does_not_log_token_or_password(monkeypatch):
    monkeypatch.setattr(smoke.subprocess, "run", lambda *args, **kwargs:
                        subprocess.CompletedProcess([], 1, "private-output", "private-error"))
    with pytest.raises(RuntimeError) as caught:
        smoke.run(["fixture", "private-argument"], {})
    assert "private" not in str(caught.value)


@pytest.mark.parametrize("field", ["devices", "settings", "samples", "events", "password", "key", "decrypted"])
def test_logical_gate_detects_each_preservation_failure(monkeypatch, tmp_path, field):
    before = {"schema": 1, "devices": [{"id": "old", "name": "miner"}], "settings": {"energy": {"price": 0.234}},
              "samples": [{"ts": 123, "hashrate": 456}], "events": [{"title": "old event"}],
              "password": "not-a-real-hash", "key": b"not-a-real-key", "decrypted": {"secret": "synthetic"}}
    after = copy.deepcopy(before)
    # Reach each preservation check after the combined candidate's migration.
    after["schema"] = 2
    after[field] = None
    monkeypatch.setattr(smoke, "logical_data", lambda _: after)
    with pytest.raises(RuntimeError, match="preservation failed") as caught:
        smoke.check_preserved(tmp_path, before)
    assert "not-a-real" not in str(caught.value) and "synthetic" not in str(caught.value)


def test_logical_gate_accepts_additive_schema_not_missing_old_values(monkeypatch, tmp_path):
    from bsmm.storage import db
    before = {"schema": 1, "devices": [{"id": "old"}], "settings": {"price": 0.234}}
    after = {"schema": 2, "devices": [{"id": "old", "new_column": 3}], "settings": {"price": 0.234, "new": True}}
    monkeypatch.setattr(db, "MIGRATIONS", [(1, ""), (2, "")])
    monkeypatch.setattr(smoke, "logical_data", lambda _: after)
    assert smoke.check_preserved(tmp_path, before) == 2
    after["schema"] = 1
    with pytest.raises(RuntimeError, match="migration gate"):
        smoke.check_preserved(tmp_path, before)


def test_legacy_source_rejects_candidate_checkout():
    with pytest.raises(RuntimeError, match=r"pinned v1\.1\.1"):
        legacy_seed.verify_source(ROOT)


def test_cold_setup_requires_empty_directory_and_literal_loopback(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(smoke, "owned_discovery_ports", smoke.contextlib.nullcontext)
    monkeypatch.setattr(smoke, "check_assets", lambda *args: calls.append("assets"))
    monkeypatch.setattr(smoke, "run", lambda *args, **kwargs: None)

    def invoke(command, env, *args):
        calls.append(args)
        if args[0] == "stop":
            return {"stopped": True}
        assert args[:4] == ("setup", "--yes", "--cidr", "127.0.0.1/32")
        assert not any(Path(env["BSMM_DATA_DIR"]).iterdir())
        return {"url": f"http://127.0.0.1:{env['BSMM_PORT']}", "overview": {"devices": 0},
                "token": "synthetic-unit-value", "steps": [{"step": "miners", "found": 0},
                {"step": "sources", "added": [], "node_candidates": []}]}

    monkeypatch.setattr(smoke, "cli", invoke)
    smoke.cold_setup(["fixture"], tmp_path, "1.1.1")
    assert "assets" in calls and ("stop",) in calls
    (tmp_path / "data/preserve").write_text("existing")
    with pytest.raises(AssertionError):
        smoke.cold_setup(["fixture"], tmp_path, "1.1.1")


def test_installed_executable_is_first_candidate_open_and_used_after_reinstall(monkeypatch, tmp_path):
    """Ordering regression only; never reported as native installer execution."""
    candidate_calls = []
    install_calls = []
    target = tmp_path / "installed app"
    baseline = {"schema": 1, "devices": [1], "samples": [1], "events": [1], "best_shares": [1],
                "channels": [1], "password": True, "key": True, "decrypted": {"bot_token": "synthetic-never-send"}}
    monkeypatch.setattr(smoke.sys, "platform", "win32")
    monkeypatch.setattr(smoke, "logical_data", lambda _: baseline)
    monkeypatch.setattr(smoke, "check_preserved", lambda *args: 1)
    monkeypatch.setattr(smoke, "check_assets", lambda *args: None)

    def run(command, env, **kwargs):
        if "--source" in command:
            return subprocess.CompletedProcess(command, 0, json.dumps({"commit": legacy_seed.LEGACY_COMMIT,
                                               "version": "1.1.1", "imports_verified": True}), "")
        if command[0] == "installer-fixture":
            install_calls.append(command)
            target.mkdir(exist_ok=True)
            (target / "bsmm.exe").touch()
            (target / "AGENT-GUIDE.txt").touch()
        elif command[0] == str(target / "unins000.exe"):
            (target / "bsmm.exe").unlink()
        else:
            pytest.fail("Unexpected executable")
        return subprocess.CompletedProcess(command, 0, "", "")

    def cli(command, env, *args):
        assert install_calls
        assert command == [str(target / "bsmm.exe")]
        candidate_calls.append(args)
        return {"stopped": True}

    monkeypatch.setattr(smoke, "run", run)
    monkeypatch.setattr(smoke, "cli", cli)
    smoke.data_upgrade(["portable-must-not-open-data"], tmp_path, "1.1.2", Path("installer-fixture"), tmp_path / "old")
    assert candidate_calls[0] == ("start",)
    assert len(install_calls) == 2
    assert candidate_calls == [("start",), ("stop",), ("start",), ("start",), ("stop",)]
