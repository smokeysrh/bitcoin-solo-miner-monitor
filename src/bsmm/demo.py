"""Demo mode: a believable fleet with history, so the app can be explored (and screenshotted) without hardware.

Everything here is synthetic. Devices run the real drivers against in-process simulators; history is
generated straight into the rollup tables; nothing touches the network or the user's real data
(demo mode uses a throw-away in-memory database).
"""

from __future__ import annotations

import math
import random
import time
from typing import Any

from bsmm.context import AppContext
from bsmm.drivers.axeos import build_info
from bsmm.drivers.cgminer import classify, parse_avalon_estats, section
from bsmm.drivers.sim import get_axeos_sim, get_cgminer_sim, reset_sims
from bsmm.models import DeviceInfo, Event, Severity
from bsmm.sim.axeos import PROFILES

DEMO_FLEET: list[dict[str, Any]] = [
    {"name": "Garage Gamma", "kind": "axeos", "profile": "gamma", "seed": 11, "tags": ["garage"], "key": "demo-gamma", "power": 18.0, "ths": 1.15},
    {"name": "Office Supra", "kind": "axeos", "profile": "supra", "seed": 12, "tags": ["office"], "key": "demo-supra", "power": 15.0, "ths": 0.69},
    {"name": "Rack GT", "kind": "axeos", "profile": "gt", "seed": 13, "tags": ["rack"], "key": "demo-gt", "power": 34.0, "ths": 2.3},
    {"name": "Basement NerdQAxe++", "kind": "axeos", "profile": "nerdqaxe", "seed": 14, "tags": ["basement"], "key": "demo-nerd", "power": 91.0, "ths": 4.8},
    {"name": "Shed Avalon Nano 3", "kind": "cgminer", "profile": "avalon_nano3", "seed": 15, "tags": ["shed"], "key": "demo-avalon", "power": 140.0, "ths": 3.9},
]


def _history_rows(device_id: str, spec: dict[str, Any], now: float, *, bucket_s: int, count: int, rng: random.Random,
                  outage: tuple[float, float] | None, reboot_at: float | None) -> list[dict[str, Any]]:
    base_hr = spec["ths"] * 1e12
    watts = spec["power"]
    per_bucket = max(1, bucket_s // 10)
    boot = reboot_at if reboot_at else now - 9 * 86400
    rows: list[dict[str, Any]] = []
    t0 = int(now // bucket_s) * bucket_s - count * bucket_s
    shares = 0.0
    for i in range(count):
        b = t0 + i * bucket_s
        online = 1.0
        if outage and outage[0] <= b < outage[1]:
            online = 0.0
        row: dict[str, Any] = {"device_id": device_id, "bucket": b, "n": per_bucket, "online": online}
        if online:
            # an offline bucket carries no readings at all (NULL), which is what the charts draw as a gap
            day = math.sin(2 * math.pi * ((b % 86400) / 86400) - 1.2)
            hr = base_hr * (1 + 0.012 * math.sin(b / 5400.0 + spec["seed"]) + rng.uniform(-0.012, 0.012))
            power = watts * (1 + rng.uniform(-0.01, 0.01))
            temp = 46 + 0.55 * (watts**0.5) * 2 + 2.5 * day + rng.uniform(-0.6, 0.6)
            shares += hr / (4096 * 4_294_967_296) * bucket_s
            row.update(
                hashrate_hs=hr, hashrate_hs_min=hr * 0.93, hashrate_hs_max=hr * 1.06,
                power_w=power, power_w_max=power * 1.02, efficiency_j_th=power / (hr / 1e12),
                temp_asic_c=temp, temp_asic_c_max=temp + 1.4, temp_vr_c=temp - 3 + 2, temp_vr_c_max=temp - 1,
                fan_pct=min(100, 28 + (temp - 40) * 2.0), fan_rpm=2800 + (temp - 40) * 30, frequency_mhz=PROFILES.get(spec["profile"], PROFILES["gamma"]).freq,
                wifi_rssi_dbm=-52 + rng.uniform(-3, 3), shares_accepted=int(shares) + 40_000, shares_rejected=int(shares * 0.006) + 120,
                best_diff=spec["ths"] * 1.1e9 + i * 1.5e6, uptime_s=int(b - boot), reject_rate_pct=0.6 + rng.uniform(-0.2, 0.3),
                voltage_in_v=5.1, core_voltage_mv=1150, pool_ping_ms=30 + rng.uniform(-6, 12), free_heap_bytes=8_000_000,
            )
        rows.append(row)
    return rows


async def seed_demo(ctx: AppContext) -> None:
    reset_sims()
    now = time.time()
    rng = random.Random(7)
    await ctx.settings.update({
        "general": {"instance_name": "Demo fleet", "onboarding_done": True},
        "energy": {"price_per_kwh": 0.14},
        "ui": {"theme": "dark"},
    })
    await ctx.store.kv_set("insight.energy_confirmed", True)
    devices = []
    for spec in DEMO_FLEET:
        key = spec["key"]
        uptime_s = 6 * 3600 if spec["profile"] == "supra" else 9 * 86400  # matches the history below
        if spec["kind"] == "axeos":
            mac = f"AA:BB:CC:{spec['seed']:02X}:00:{spec['seed']:02X}"
            sim = get_axeos_sim(key, spec["profile"], spec["seed"], mac=mac, hostname=key)
            sim.prime(uptime_s)
            info = build_info(key, 80, sim.info(), None)
            info.driver = "sim"
            info.extra["sim_kind"] = "axeos"
        else:
            sim_c = get_cgminer_sim(key, spec["profile"], spec["seed"])
            sim_c.prime(uptime_s)
            family, model = classify(sim_c.reply("version")["VERSION"][0])
            est = parse_avalon_estats(section(sim_c.reply("estats"), "STATS"))
            info = DeviceInfo(driver="sim", family=family, model=model, host=key, port=4028, serial=est.get("dna"), firmware="25021401_4ec6bb0",
                              extra={"sim_kind": "cgminer", "monitor_only": True, "power_override_w": spec["power"]})
        dev = await ctx.store.add_device(info, name=spec["name"], tags=spec["tags"])
        devices.append((dev, spec))

    # 24 h of minute rollups, 30 d of hour rollups, 90 d of day rollups
    for dev, spec in devices:
        outage = (now - 20 * 3600, now - 20 * 3600 + 14 * 60) if spec["profile"] == "gt" else None
        for table, bucket_s, count in (("samples_1m", 60, 1440), ("samples_1h", 3600, 30 * 24), ("samples_1d", 86400, 90)):
            rows = _history_rows(dev.id, spec, now, bucket_s=bucket_s, count=count, rng=rng, outage=outage if bucket_s <= 3600 else None,
                                 reboot_at=now - 6 * 3600 if spec["profile"] == "supra" else None)
            await ctx.store.samples.insert_rollup_rows(table, rows)
        await ctx.store.add_best_share(dev.id, spec["ths"] * 1.1e9, ts=now - 3 * 86400)

    gt = next(d for d, s in devices if s["profile"] == "gt")
    supra = next(d for d, s in devices if s["profile"] == "supra")
    nerd = next(d for d, s in devices if s["profile"] == "nerdqaxe")
    history = [
        (now - 6 * 86400, "difficulty_adjusted", Severity.INFO, "Difficulty rose 2.31%", None, None, "Network difficulty is now 1.406e+14."),
        (now - 2 * 86400 - 3600, "new_best_share", Severity.SUCCESS, f"New best share on {nerd.name}", nerd.id, None, "Difficulty 51.0G (was 38.2G). That is 0.0363% of the way to a block."),
        (now - 20 * 3600, "device_offline", Severity.CRITICAL, f"{gt.name} is offline", gt.id, None, "Last error: connection refused"),
        (now - 20 * 3600 + 14 * 60, "device_online", Severity.SUCCESS, f"{gt.name} is back online", gt.id, None, "It was unreachable for 14m."),
        (now - 6 * 3600, "device_restarted", Severity.INFO, f"{supra.name} restarted", supra.id, None, None),
    ]
    for ts, type_, sev, title, dev_id, _unused, body in history:
        await ctx.store.add_event(Event(ts=ts, type=type_, severity=sev, title=title, device_id=dev_id, body=body, ack_ts=ts + 60))

    hashes = sum(s["ths"] for _, s in devices) * 1e12 * 12 * 86400
    await ctx.store.kv_set("luck.total_hashes", hashes)
    await ctx.store.kv_set("luck.expected_blocks", hashes / (140_577_680_051_919.6 * 4_295_032_833.0000153))
    await ctx.store.kv_set("luck.since", now - 12 * 86400)
    await ctx.store.kv_set("blocks.last_checked", 972_175)
