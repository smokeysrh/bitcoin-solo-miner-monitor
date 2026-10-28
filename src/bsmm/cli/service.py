"""Generate auto-start definitions (systemd / launchd / Windows Task Scheduler) for `bsmm service`."""

from __future__ import annotations

import plistlib
import shutil
import subprocess
import sys
from pathlib import Path


def exe_command(port: int | None = None, data_dir: str | None = None) -> list[str]:
    exe = shutil.which("bsmm") if not getattr(sys, "frozen", False) else sys.executable
    base = [exe] if exe else [sys.executable, "-m", "bsmm"]
    base.append("serve")
    if port:
        base += ["--port", str(port)]
    if data_dir:
        base += ["--data-dir", data_dir]
    return base


def systemd_unit(cmd: list[str], user_unit: bool = True) -> str:
    return f"""[Unit]
Description=Bitcoin Solo Miner Monitor
After=network-online.target
Wants=network-online.target

[Service]
ExecStart={" ".join(_q(c) for c in cmd)}
Restart=on-failure
RestartSec=5
{"" if user_unit else "User=bsmm"}
[Install]
WantedBy={"default.target" if user_unit else "multi-user.target"}
"""


def launchd_plist(cmd: list[str]) -> str:
    return plistlib.dumps({"Label": "com.github.smokeysrh.bsmm", "ProgramArguments": cmd,
                          "RunAtLoad": True, "KeepAlive": True}).decode("utf-8")


def windows_task(cmd: list[str]) -> list[str]:
    tr = subprocess.list2cmdline(cmd)
    return ["schtasks", "/Create", "/F", "/SC", "ONLOGON", "/TN", "BitcoinSoloMinerMonitor", "/TR", tr, "/RL", "LIMITED"]


def systemd_path() -> Path:
    return Path.home() / ".config" / "systemd" / "user" / "bsmm.service"


def launchd_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / "com.github.smokeysrh.bsmm.plist"


def _q(part: str) -> str:
    return f'"{part}"' if " " in part else part
