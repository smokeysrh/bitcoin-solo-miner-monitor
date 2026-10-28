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


def run(command: list[str], env: dict[str, str], *, success: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=90, check=False)  # noqa: S603
    if success and result.returncode != 0:
        raise RuntimeError(f"smoke command failed: {result.stdout[-1000:]} {result.stderr[-1000:]}")
    return result


def cli(command: list[str], env: dict[str, str], *args: str) -> dict:
    return json.loads(run([*command, *args, "--json"], env).stdout)


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


def smoke(command: list[str], root: Path, version: str, installer: Path | None) -> None:
    data = root / "data"
    home = root / "home"
    cache = root / "cache"
    for path in (data, home, cache):
        path.mkdir(parents=True)
    env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home), "LOCALAPPDATA": str(home / "local"),
           "APPDATA": str(home / "roaming"), "XDG_CACHE_HOME": str(cache), "TMP": str(root), "TEMP": str(root),
           "BSMM_DATA_DIR": str(data), "BSMM_HOST": "127.0.0.1", "BSMM_LIVE": "0", "BSMM_OFFLINE": "1",
           "BSMM_NO_UPDATE_CHECK": "1"}
    env.pop("BSMM_URL", None)
    env.pop("BSMM_TOKEN", None)
    chosen = port()
    env["BSMM_PORT"] = str(chosen)
    base = f"http://127.0.0.1:{chosen}"
    assert run([*command, "version"], env).stdout.strip() == version
    sentinel = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(180)"], env=env)
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
        if installer is not None:
            if sys.platform != "win32":
                raise RuntimeError("Native Windows installer checks cannot run on Linux")
            target = root / "installed app"
            install = [str(installer), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", f"/DIR={target}"]
            run(install, env)
            command = [str(target / "bsmm.exe")]
            assert (target / "AGENT-GUIDE.txt").is_file()
            run(["powershell", "-NoProfile", "-File", str(Path(__file__).with_name("check-native.ps1")),
                 "-Exe", command[0], "-Installer", str(installer), "-Version", version, "-Shortcuts"], env)
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
            before = saved_data(data)
            run([str(target / "unins000.exe"), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"], env)
            deadline = time.monotonic() + 20
            while (target / "bsmm.exe").exists() and time.monotonic() < deadline:
                time.sleep(0.2)
            assert not (target / "bsmm.exe").exists()
            assert saved_data(data) == before and sentinel.poll() is None
            assert credentials(data) == credential_snapshot
        print(json.dumps({"ok": True, "platform": sys.platform, "version": version,
                          "checks": ["version", "assets", "repeat-start", "safe-stop", "stale-pid", "failed-start"],
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
    parser.add_argument("--expected-version", required=True)
    args = parser.parse_args()
    command = [str(args.exe.resolve())] if args.exe else [sys.executable, "-m", "bsmm"]
    with tempfile.TemporaryDirectory(prefix="bsmm-native-") as folder:
        smoke(command, Path(folder), args.expected_version, args.installer.resolve() if args.installer else None)
