"""Disposable real-process smoke for source/frozen CLI; installer checks are Windows-only.

No miners, chain, pools, notification destinations, service registration or live data.
Every server is offline on a reserved loopback port. Only our sentinel child is
terminated by its Popen handle in cleanup; bsmm must never signal it.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

DISCOVERY_PORTS = (80, 4028, 8332, 2019, 3334, 3006)
LEGACY_COMMIT = "5674faad417911c92c526ebf5bf78a57b09ed1af"
NATIVE_DIAGNOSTIC_LIMIT = 4096


def native_check(exe: str, installer: Path, version: str, env: dict[str, str]) -> None:
    result = run(["powershell", "-NoProfile", "-File", str(Path(__file__).with_name("check-native.ps1")),
                  "-Exe", exe, "-Installer", str(installer), "-Version", version, "-Shortcuts"], env, success=False)
    # This one metadata-only command has a strict output schema. General run/CLI
    # output remains withheld, including setup's one-time token and all stderr.
    stages = {"exe-resource", "installer-resource", "shortcut-shell", "start-shortcut",
              "stop-shortcut", "guide-shortcut", "complete"}
    versions = {"shell_version", "exe_product", "exe_file", "installer_product", "installer_file"}
    flags = {"ok", "shortcut_exists", "target_matches", "arguments_match", "guide_exists"}
    metadata = None
    try:
        metadata = json.loads(result.stdout) if len(result.stdout) <= NATIVE_DIAGNOSTIC_LIMIT else None
        valid = (isinstance(metadata, dict) and metadata.get("stage") in stages
                 and type(metadata.get("ok")) is bool
                 and all((key == "stage" and value in stages)
                         or (key in flags and type(value) is bool)
                         or (key in versions and isinstance(value, str)
                             and (value == "withheld" or re.fullmatch(r"\d{1,5}\.\d{1,5}\.\d{1,5}(?:\.\d{1,5}|(?:a|b|rc)\d{1,5})?", value)))
                         for key, value in metadata.items()))
    except (ValueError, TypeError):
        valid = False
    if not valid or not isinstance(metadata, dict):
        # Shell policy/parse failures can occur before our script emits metadata.
        policy = "PSSecurityException" in result.stderr or "UnauthorizedAccess" in result.stderr
        print(json.dumps({"native_check": "metadata-unavailable", "exit": result.returncode,
                          "shell_policy_error": policy}), flush=True)
        raise RuntimeError("Native check metadata unavailable; raw output withheld")
    print(json.dumps({"native_check": metadata, "exit": result.returncode}), flush=True)
    if result.returncode != 0 or not metadata["ok"] or metadata["stage"] != "complete":
        raise RuntimeError("Native resource/shortcut check failed; see bounded metadata")


def run(command: list[str], env: dict[str, str], *, success: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=90, check=False)  # noqa: S603
    except subprocess.TimeoutExpired:
        raise RuntimeError("smoke command timed out; captured output withheld") from None
    if success and result.returncode != 0:
        # setup prints a one-time bearer token. Never disclose stdout/stderr or argv,
        # even on failures (including JSON decode failures below).
        raise RuntimeError(f"smoke command failed (exit {result.returncode}); captured output withheld")
    return result


def cli(command: list[str], env: dict[str, str], *args: str) -> dict:
    output = run([*command, *args, "--json"], env).stdout
    try:
        value = json.loads(output)  # consumes exactly one document, rejects trailing output
    except ValueError:
        raise RuntimeError("CLI stdout was not one JSON document; output withheld") from None
    if not isinstance(value, dict):
        raise RuntimeError("CLI JSON must be an object")
    return value


def port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def fetch(base: str, path: str) -> bytes:
    # Base is always constructed here from a reserved loopback port, never user input.
    with urlopen(base + path, timeout=10) as response:  # noqa: S310
        assert response.status == 200
        return response.read()


def check_assets(base: str, version: str) -> None:
    assert json.loads(fetch(base, "/api/v1/health"))["version"] == version
    html = fetch(base, "/").decode()
    assets = re.findall(r'(?:src|href)="(/assets/[^" ]+)"', html)
    assert assets and "<div id=\"app\">" in html
    assert all(len(fetch(base, asset)) > 0 for asset in assets)
    guide = fetch(base, "/llms.txt").decode()
    assert version in guide and "MCP" in guide


def saved_data(data: Path) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in data.iterdir()
            if p.is_file() and p.name not in {"bsmm.pid", "bsmm.lock", "bsmm.log", "bsmm.ready", "bsmm.stop"}
            and not p.name.startswith("bsmm.log.")}


def credentials(data: Path) -> tuple[str, bytes]:
    with contextlib.closing(sqlite3.connect(f"file:{(data / 'bsmm.db').as_posix()}?mode=ro", uri=True)) as db:
        stored = db.execute("SELECT value FROM kv WHERE key = ?", ("auth.password",)).fetchone()[0]
    return stored, (data / "secret.key").read_bytes()


def isolated_env(root: Path, data: Path) -> dict[str, str]:
    # No inherited password, token, key, demo switch, remote URL or proxy can
    # silently redirect this fixture into a real account/service/data directory.
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("BSMM_") and key.lower() not in {"http_proxy", "https_proxy", "all_proxy"}}
    home, cache = root / "home", root / "cache"
    for path in (data, home, cache):
        path.mkdir(parents=True, exist_ok=True)
    env.update({"HOME": str(home), "USERPROFILE": str(home), "LOCALAPPDATA": str(home / "local"),
                "APPDATA": str(home / "roaming"), "XDG_CACHE_HOME": str(cache),
                "XDG_CONFIG_HOME": str(home / "config"), "XDG_DATA_HOME": str(home / "data"),
                "XDG_STATE_HOME": str(home / "state"), "TMPDIR": str(root), "TMP": str(root), "TEMP": str(root),
                "NO_PROXY": "127.0.0.1,localhost", "BSMM_DATA_DIR": str(data), "BSMM_HOST": "127.0.0.1",
                "BSMM_LIVE": "0", "BSMM_OFFLINE": "1", "BSMM_NO_UPDATE_CHECK": "1"})
    return env


@contextlib.contextmanager
def owned_discovery_ports():
    # Bind WITHOUT listening: discovery gets connection-refused, never contacts
    # installed services. Fail closed before setup if any required port is busy.
    # The real discovery code is still exercised, not patched or replaced.
    with contextlib.ExitStack() as stack:
        for number in DISCOVERY_PORTS:
            sock = stack.enter_context(socket.socket())
            if sys.platform == "win32":
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                sock.bind(("127.0.0.1", number))
            except OSError as error:
                raise RuntimeError(f"Cannot own discovery fixture port {number} (errno {error.errno}); setup not run") from None
        yield


def cold_setup(command: list[str], root: Path, version: str) -> None:
    data = root / "data"
    env = isolated_env(root, data)
    chosen = port()
    env["BSMM_PORT"] = str(chosen)
    assert not any(data.iterdir())
    with owned_discovery_ports():
        try:
            result = cli(command, env, "setup", "--yes", "--cidr", "127.0.0.1/32",
                         "--port", str(chosen), "--data-dir", str(data))
            assert result["url"] == f"http://127.0.0.1:{chosen}"
            assert result["overview"]["devices"] == 0
            assert isinstance(result.pop("token", None), str)
            steps = {item["step"]: item for item in result["steps"]}
            assert steps["miners"]["found"] == 0 and steps["sources"]["added"] == []
            assert steps["sources"]["node_candidates"] == []
            check_assets(result["url"], version)
            assert cli(command, env, "stop")["stopped"]
            assert not (data / "bsmm.pid").exists()
        finally:
            run([*command, "stop"], env)


def logical_data(data: Path) -> dict:
    """Read only: never invoke candidate Store/migrations before installed start.

    Compare old logical columns/values, not DB/WAL bytes or newly added columns.
    Secrets live only in memory and must never be rendered in failure messages.
    """
    from cryptography.fernet import Fernet

    tables = ("devices", "samples", "samples_1m", "samples_1h", "samples_1d", "events", "best_shares", "channels")
    with contextlib.closing(sqlite3.connect(f"file:{(data / 'bsmm.db').as_posix()}?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        result: dict = {table: [dict(row) for row in db.execute(f"SELECT * FROM {table} ORDER BY 1, 2")]  # noqa: S608
                  for table in tables}
        result["settings"] = json.loads(db.execute("SELECT value FROM kv WHERE key='settings'").fetchone()[0])
        result["schema"] = db.execute("PRAGMA user_version").fetchone()[0]
    result["password"], result["key"] = credentials(data)
    encrypted = result["channels"][0]["secret_enc"]
    assert encrypted.startswith("enc:v1:")
    result["decrypted"] = json.loads(Fernet(result["key"]).decrypt(encrypted[len("enc:v1:"):].encode()))
    return result


def contains(actual, expected) -> bool:
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(k in actual and contains(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and all(any(contains(row, old) for row in actual) for old in expected)
    return actual == expected


def check_preserved(data: Path, before: dict) -> int:
    after = logical_data(data)
    from bsmm.storage.db import MIGRATIONS
    if after["schema"] != max(number for number, _ in MIGRATIONS):
        raise RuntimeError("Candidate schema migration gate failed")
    if not contains(after, {k: v for k, v in before.items() if k != "schema"}):
        raise RuntimeError("Legacy logical data/credential preservation failed; values withheld")
    return after["schema"]


def data_upgrade(command: list[str], root: Path, version: str, installer: Path | None, legacy_source: Path) -> None:
    data = root / "data"
    env = isolated_env(root, data)
    env["BSMM_PORT"] = str(port())
    base = f"http://127.0.0.1:{env['BSMM_PORT']}"
    seed = json.loads(run([sys.executable, str(Path(__file__).with_name("legacy_seed.py")),
                          "--source", str(legacy_source), "--data", str(data)], env).stdout)
    assert seed["commit"] == LEGACY_COMMIT and seed["version"] == "1.1.1" and seed["imports_verified"]
    before = logical_data(data)
    assert all(before[name] for name in ("devices", "samples", "events", "best_shares", "channels", "password", "key"))
    assert before["decrypted"] == {"bot_token": "synthetic-never-send"}
    (data / "preserve.txt").write_text("v1.1.1 user-owned sentinel", encoding="utf-8")
    target = root / "installed app"
    if installer is not None:
        if sys.platform != "win32":
            raise RuntimeError("Native Windows installer checks cannot run on Linux")
        assert not target.exists()
        install = [str(installer), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", f"/DIR={target}"]
        run(install, env)
        command = [str(target / "bsmm.exe")]
        assert (target / "AGENT-GUIDE.txt").is_file()
        # Fresh target + skipifsilent means installer cannot auto-start the portable
        # build. Installed start below is the FIRST candidate open of legacy data.
        assert logical_data(data) == before
    try:
        cli(command, env, "start")
        check_assets(base, version)
        assert cli(command, env, "stop")["stopped"]
        schema = check_preserved(data, before)
        cli(command, env, "start")  # reopen the migrated database
        if installer is not None:
            run(install, env)  # same-candidate reinstall while installed app runs
            cli(command, env, "start")
        check_assets(base, version)
        assert cli(command, env, "stop")["stopped"]
        check_preserved(data, before)
        if installer is not None:
            run([str(target / "unins000.exe"), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"], env)
            deadline = time.monotonic() + 20
            while (target / "bsmm.exe").exists() and time.monotonic() < deadline:
                time.sleep(0.2)
            assert not (target / "bsmm.exe").exists()
            check_preserved(data, before)
        assert (data / "preserve.txt").read_text() == "v1.1.1 user-owned sentinel"
        print(json.dumps({"legacy_data_upgrade": True, "legacy_commit": LEGACY_COMMIT,
                          "schema_before": before["schema"], "schema_after": schema,
                          "logical_data_preserved": True, "credentials_preserved": True,
                          "reopen": True, "installer_reinstall_uninstall": installer is not None}))
    finally:
        if Path(command[0]).exists():
            run([*command, "stop"], env)


def smoke(command: list[str], root: Path, version: str, installer: Path | None, legacy_source: Path) -> None:
    data = root / "data"
    env = isolated_env(root, data)
    chosen = port()
    env["BSMM_PORT"] = str(chosen)
    base = f"http://127.0.0.1:{chosen}"
    assert run([*command, "version"], env).stdout.strip() == version
    sentinel = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"], env=env)
    try:
        started = cli(command, env, "start", "--port", str(chosen))
        pid = started["pid"]
        check_assets(base, version)
        for _ in range(2):
            repeated = cli(command, env, "start", "--port", str(chosen))
            assert repeated["already"] and repeated["pid"] == pid
            check_assets(base, version)
        assert cli(command, env, "stop")["stopped"]
        assert sentinel.poll() is None
        # Forged PID-only state must not stop this unrelated live process.
        (data / "bsmm.pid").write_text(str(sentinel.pid))
        stopped = cli(command, env, "stop")
        assert not stopped["stopped"] and sentinel.poll() is None
        assert not (data / "bsmm.pid").exists()
        (data / "bsmm.pid").write_text(str(sentinel.pid))
        refused = run([*command, "start"], env, success=False)
        assert refused.returncode != 0 and sentinel.poll() is None
        assert not (data / "bsmm.pid").exists()
        # A held port makes startup fail and clears its own dead-child state.
        with socket.socket() as busy:
            busy.bind(("127.0.0.1", 0))
            busy.listen()
            failed = run([*command, "start", "--port", str(busy.getsockname()[1])], env, success=False)
            assert failed.returncode != 0 and not (data / "bsmm.pid").exists()
        # Real persistent credentials, created offline in this disposable data dir.
        run([*command, "password", "--offline-local", "--data-dir", str(data), "--password", "disposable-smoke-password"], env)
        (data / "preserve.txt").write_text("user-owned sentinel", encoding="utf-8")
        before = saved_data(data)
        credential_snapshot = credentials(data)
        assert before
        print(json.dumps({"fresh_lifecycle": True, "platform": sys.platform,
                          "checks": ["version", "assets", "repeat-start", "safe-stop", "stale-pid", "failed-start"]}))
        cold_command = command
        if installer is not None:
            if sys.platform != "win32":
                raise RuntimeError("Native Windows installer checks cannot run on Linux")
            target = root / "installed app"
            install = [str(installer), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", f"/DIR={target}"]
            run(install, env)
            command = [str(target / "bsmm.exe")]
            cold_command = command
            assert (target / "AGENT-GUIDE.txt").is_file()
            native_check(command[0], installer, version, env)
            assert saved_data(data) == before
            cli(command, env, "start")
            check_assets(base, version)
            cli(command, env, "stop")
            # Capture post-runtime DB bytes, then reinstall with the server running:
            # installer must stop exactly its own instance and preserve stored values.
            before = saved_data(data)
            cli(command, env, "start")
            run(install, env)
            assert sentinel.poll() is None
            cli(command, env, "start")
            check_assets(base, version)
            cli(command, env, "stop")
            assert (data / "preserve.txt").read_text() == "user-owned sentinel"
            assert credentials(data) == credential_snapshot
            # An unreachable explicit target must not reset the local password.
            bad = run([*command, "password", "--url", base, "--password", "replacement"], env, success=False)
            assert bad.returncode != 0  # server is offline; must not reset the local password
            assert credentials(data) == credential_snapshot
            cold_setup(cold_command, root / "cold-setup", version)
            before = saved_data(data)
            run([str(target / "unins000.exe"), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"], env)
            deadline = time.monotonic() + 20
            while (target / "bsmm.exe").exists() and time.monotonic() < deadline:
                time.sleep(0.2)
            assert not (target / "bsmm.exe").exists()
            assert saved_data(data) == before and sentinel.poll() is None
            assert credentials(data) == credential_snapshot
        else:
            cold_setup(cold_command, root / "cold-setup", version)
        data_upgrade(cold_command, root / "legacy-upgrade", version, installer, legacy_source)
        assert sentinel.poll() is None
        print(json.dumps({"ok": True, "platform": sys.platform, "version": version,
                          "checks": ["version", "assets", "repeat-start", "safe-stop", "stale-pid", "failed-start",
                                     "cold-setup-json", "v1.1.1-data-upgrade"],
                          "installer": installer is not None}))
    finally:
        # Always request cooperative cleanup of only the instance in our data dir.
        if Path(command[0]).exists():
            result = run([*command, "stop"], env, success=False)
            if result.returncode:
                print("smoke cleanup could not confirm stop", file=sys.stderr)
        sentinel.terminate()
        sentinel.wait(timeout=10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--installer", type=Path)
    parser.add_argument("--legacy-source", type=Path, required=True,
                        help="Separate clean checkout of pinned v1.1.1 source (not an old Windows installer)")
    parser.add_argument("--expected-version", required=True)
    args = parser.parse_args()
    command = [str(args.exe.resolve())] if args.exe else [sys.executable, "-m", "bsmm"]
    with tempfile.TemporaryDirectory(prefix="bsmm-native-") as folder:
        smoke(command, Path(folder), args.expected_version, args.installer.resolve() if args.installer else None,
              args.legacy_source.resolve())
