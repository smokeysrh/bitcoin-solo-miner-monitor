"""Generate auto-start definitions (systemd / launchd / Windows Task Scheduler) for `bsmm service`."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


def exe_command(port: int | None = None, data_dir: str | None = None) -> list[str]:
    exe = shutil.which("bsmm")
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
    args = "\n".join(f"    <string>{c}</string>" for c in cmd)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.github.smokeysrh.bsmm</string>
  <key>ProgramArguments</key><array>
{args}
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict></plist>
"""


def windows_task(cmd: list[str]) -> list[str]:
    tr = " ".join(f'"{c}"' if " " in c else c for c in cmd)
    return ["schtasks", "/Create", "/F", "/SC", "ONLOGON", "/TN", "BitcoinSoloMinerMonitor", "/TR", tr, "/RL", "LIMITED"]


def systemd_path() -> Path:
    return Path.home() / ".config" / "systemd" / "user" / "bsmm.service"


def launchd_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / "com.github.smokeysrh.bsmm.plist"


def _q(part: str) -> str:
    return f'"{part}"' if " " in part else part
