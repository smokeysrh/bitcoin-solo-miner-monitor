"""Seed disposable v1.1.1 data using only the pinned application's Store/Auth code.

Run as a separate interpreter, never import the candidate before the old package.
No application context, server, discovery, poller or notification sender is started.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

LEGACY_COMMIT = "5674faad417911c92c526ebf5bf78a57b09ed1af"
LEGACY_VERSION = "1.1.1"
CHANNEL_ID = "channel-upgrade-fixture"


def verify_source(source: Path) -> None:
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("Git is required to verify the immutable legacy source")
    head = subprocess.run([git, "-C", str(source), "rev-parse", "HEAD"],  # noqa: S603
                          check=True, capture_output=True, text=True).stdout.strip()
    if head != LEGACY_COMMIT:
        raise RuntimeError("Legacy source is not the pinned v1.1.1 commit")
    subprocess.run([git, "-C", str(source), "diff", "--exit-code", "HEAD", "--", "src/bsmm"],  # noqa: S603
                   check=True, capture_output=True)


def prepare_source(source: Path, data: Path) -> None:
    verify_source(source)
    if data.exists() and any(data.iterdir()):
        raise RuntimeError("Legacy seeding requires an owned empty data directory")
    if any(name == "bsmm" or name.startswith("bsmm.") for name in sys.modules):
        raise RuntimeError("Candidate modules were imported before legacy seeding")
    sys.path.insert(0, str(source / "src"))


def verify_imports(source: Path) -> None:
    for name, module in tuple(sys.modules.items()):
        if name == "bsmm" or name.startswith("bsmm."):
            filename = module.__file__
            if filename is None or not Path(filename).resolve().is_relative_to(source / "src/bsmm"):
                raise RuntimeError("Legacy import escaped the pinned checkout")


async def seed(source: Path, data: Path) -> None:
    import bsmm
    from bsmm.auth import AuthService
    from bsmm.config import RuntimeConfig
    from bsmm.models import Channel, DeviceInfo, Event, Telemetry
    from bsmm.settings import SettingsService
    from bsmm.storage.samples import telemetry_to_row
    from bsmm.storage.store import Store

    if bsmm.__version__ != LEGACY_VERSION:
        raise RuntimeError("Legacy imported version mismatch")
    verify_imports(source)
    store = await Store.open(RuntimeConfig(data_dir=data, offline=True, no_update_check=True))
    try:
        now = int(time.time())
        device = await store.add_device(DeviceInfo(host="127.0.0.1", port=1, driver="axeos", family="bitaxe",
                                                  model="upgrade-fixture"), name="v1.1.1 preserved miner",
                                        tags=["upgrade-fixture"], group="preserved-group")
        device.enabled = False  # the candidate must never poll even this synthetic device
        device.allow_control = False
        device.notes = "v1.1.1 preservation sentinel"
        await store.save_device(device)
        settings = SettingsService(store)
        await settings.load()
        await settings.update({"general": {"instance_name": "v1.1.1 upgrade fixture", "first_run_at": now,
                                           "onboarding_done": True},
                               "energy": {"price_per_kwh": 0.234}, "ui": {"theme": "light"},
                               "network": {"use_public_apis": False, "price_source": "none"},
                               "auth": {"mode": "password"}})
        await AuthService(store).set_password("disposable-upgrade-password")
        await store.save_channel(Channel(id=CHANNEL_ID, kind="telegram", name="Disabled upgrade credential",
                                         enabled=False, config={}), {"bot_token": "synthetic-never-send"})
        await store.samples.write([telemetry_to_row(device.id, Telemetry(ts=now - 60, online=True,
                                                                         hashrate_hs=123456789, power_w=12.5))])
        await store.add_event(Event(ts=now - 60, type="upgrade.fixture", device_id=device.id,
                                    title="Preserved v1.1.1 history", data={"fixture": True}))
        await store.add_best_share(device.id, 987654321, now - 60)
        schema = await store.db.schema_version()
        if not await AuthService(store).check_password("disposable-upgrade-password"):
            raise RuntimeError("Legacy password fixture failed")
        if await store.channel_secret(CHANNEL_ID) != {"bot_token": "synthetic-never-send"}:
            raise RuntimeError("Legacy credential fixture failed")
    finally:
        await store.close()
    print(json.dumps({"seeded": True, "commit": LEGACY_COMMIT, "version": LEGACY_VERSION,
                      "imports_verified": True, "schema": schema}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    args = parser.parse_args()
    prepare_source(args.source.resolve(), args.data.resolve())
    asyncio.run(seed(args.source.resolve(), args.data.resolve()))
