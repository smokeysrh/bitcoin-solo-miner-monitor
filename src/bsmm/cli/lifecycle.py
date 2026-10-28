"""Identity-bound background instances. No PID-only signals, on any platform.

A data-directory lock serializes start/stop. OS creation time, executable and
command line bind the saved PID; a per-launch nonce binds cooperative shutdown.
Old numeric PID files are not authority to stop a process.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import psutil

from bsmm.cli.client import CliError

if TYPE_CHECKING:
    import uvicorn

POLL_SECONDS = 0.2
STOP_SECONDS = 15.0
START_ATTEMPTS = 150


def alive(pid: int) -> bool:
    try:
        proc = psutil.Process(pid)
        return bool(proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE)
    except psutil.NoSuchProcess:
        return False
    except psutil.AccessDenied as e:
        raise CliError("Cannot verify the background process identity; no process was stopped.") from e


@contextlib.contextmanager
def locked(data: Path) -> Iterator[None]:
    # Keep the lock inode: unlinking it permits a third process to lock a new file.
    with (data / "bsmm.lock").open("a+b") as handle:
        handle.seek(0)
        if sys.platform == "win32":
            import msvcrt

            if not handle.read(1):
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as e:
                raise CliError("Another start/stop operation is in progress. Try again shortly.") from e
        else:
            import fcntl

            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as e:
                raise CliError("Another start/stop operation is in progress. Try again shortly.") from e
        try:
            yield
        finally:
            if sys.platform == "win32":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def save_process(data: Path, pid: int, token: str, port: int) -> None:
    try:
        proc = psutil.Process(pid)
        record = {"pid": pid, "created": proc.create_time(), "exe": proc.exe(), "argv": proc.cmdline(),
                  "data": str(data.resolve()), "token": token, "port": port}
    except psutil.Error as e:
        raise CliError("The new process exited or its identity could not be read.") from e
    (data / "bsmm.pid").write_text(json.dumps(record), encoding="utf-8")


def read_record(data: Path) -> dict[str, Any]:
    try:
        value = json.loads((data / "bsmm.pid").read_text(encoding="utf-8"))
    except (ValueError, FileNotFoundError):
        return {}
    return value if isinstance(value, dict) else {}


def owned_process(data: Path, record: dict[str, Any]) -> psutil.Process | None:
    try:
        pid, created, exe, argv, token = (record[k] for k in ("pid", "created", "exe", "argv", "token"))
        if (type(pid) is not int or pid <= 0 or not isinstance(token, str) or not token
                or type(record["port"]) is not int or not 1 <= record["port"] <= 65535
                or record["data"] != str(data.resolve()) or not isinstance(argv, list)):
            return None
        # Require the actual bsmm serve invocation, not merely matching arbitrary
        # process metadata supplied by a malformed/stale record.
        prefix = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, "-m", "bsmm"]
        if argv[:len(prefix) + 1] != [*prefix, "serve"]:
            return None
        if argv[argv.index("--data-dir") + 1] != str(data.resolve()) or argv[argv.index("--managed-token") + 1] != token:
            return None
        proc = psutil.Process(pid)
        if proc.create_time() != created or proc.exe() != exe or proc.cmdline() != argv:
            return None
        return proc if proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE else None
    except (KeyError, ValueError, IndexError, TypeError, psutil.NoSuchProcess):
        return None
    except psutil.AccessDenied as e:
        raise CliError("Cannot verify the background process identity; state was retained.") from e


def clear(data: Path) -> None:
    for name in ("bsmm.pid", "bsmm.ready", "bsmm.stop"):
        (data / name).unlink(missing_ok=True)


def ready(data: Path, token: str) -> bool:
    try:
        return (data / "bsmm.ready").read_text(encoding="utf-8") == token
    except FileNotFoundError:
        return False


def request_stop(data: Path, token: str) -> None:
    (data / "bsmm.stop").write_text(token, encoding="utf-8")


async def run_managed(server: uvicorn.Server, data: Path, token: str) -> None:
    async def watch() -> None:
        announced = False
        while True:
            if server.started and not announced:
                (data / "bsmm.ready").write_text(token, encoding="utf-8")
                announced = True
            try:
                if (data / "bsmm.stop").read_text(encoding="utf-8") == token:
                    server.should_exit = True
                    return
            except FileNotFoundError:
                pass  # no shutdown requested
            await asyncio.sleep(POLL_SECONDS)

    watcher = asyncio.create_task(watch())
    try:
        await server.serve()
    finally:
        watcher.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await watcher
