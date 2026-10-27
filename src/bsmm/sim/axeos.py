"""A fake AxeOS / ESP-Miner device that speaks the real HTTP API.

Used by the test-suite, by ``bsmm dev-sim`` (develop without hardware) and for safely trying every
control action (restart, pool change, tuning...) without touching a real miner.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

EXAMPLE_ADDR = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"


@dataclass(frozen=True)
class Profile:
    name: str
    device_model: str | None
    asic: str
    asic_count: int
    board: str
    base_ghs: float
    watts: float
    freq: int
    core_mv: int
    small_cores: int
    version: str = "v2.12.0"
    temp_per_w: float = 0.9  # chip temperature rise per watt (a big fan means less)
    freq_options: tuple[int, ...] = (400, 425, 450, 475, 490, 500, 525, 550, 575, 600)
    volt_options: tuple[int, ...] = (1100, 1150, 1200, 1250, 1300)
    extra: dict[str, Any] = field(default_factory=dict)


PROFILES: dict[str, Profile] = {
    "gamma": Profile("gamma", "Gamma", "BM1370", 1, "601", 1150.0, 18.0, 525, 1150, 2040, temp_per_w=1.0),
    "supra": Profile("supra", "Supra", "BM1368", 1, "402", 690.0, 15.0, 490, 1166, 1276, temp_per_w=1.2),
    "gt": Profile("gt", "GT", "BM1370", 2, "801", 2300.0, 34.0, 575, 1150, 2040, temp_per_w=0.55),
    "nerdqaxe": Profile("nerdqaxe", "NerdQAxe++", "BM1370", 4, "", 4800.0, 91.0, 600, 1150, 2040, version="v1.0.30", temp_per_w=0.2),
}


class AxeOSSim:
    def __init__(self, profile: str | Profile = "gamma", *, seed: int | None = None, mac: str | None = None,
                 hostname: str | None = None, pool: tuple[str, int, str] = ("192.168.1.10", 2018, f"{EXAMPLE_ADDR}.sim1")) -> None:
        self.profile = PROFILES[profile] if isinstance(profile, str) else profile
        self.rng = random.Random(seed)
        self.started = time.time()
        n = self.rng.randrange(1, 255)
        self.mac = mac or f"AA:BB:CC:{n:02X}:{self.rng.randrange(256):02X}:{self.rng.randrange(256):02X}"
        self.hostname = hostname or f"sim-{self.profile.name}"
        self.settings: dict[str, Any] = {
            "frequency": self.profile.freq,
            "coreVoltage": self.profile.core_mv,
            "autofanspeed": 1,
            "manualFanSpeed": 60,
            "temptarget": 60,
            "stratumURL": pool[0],
            "stratumPort": pool[1],
            "stratumUser": pool[2],
            "fallbackStratumURL": "solo.ckpool.org",
            "fallbackStratumPort": 3333,
            "fallbackStratumUser": pool[2],
            "hostname": self.hostname,
        }
        self.paused = False
        self.restarts = 0
        self.identified = 0
        self.shares_accepted = 0
        self.shares_rejected = 0
        self.best_diff = self.rng.uniform(2e8, 4e9)
        self.best_session = self.best_diff * 0.2
        self.blocks_found = 0
        self.last_tick = time.time()
        self.calls: list[tuple[str, str, Any]] = []  # (method, path, body) - handy for assertions
        self.fail_next = 0  # make the next N requests fail with HTTP 500

    def prime(self, uptime_s: float) -> None:
        """Pretend the device has already been mining for ``uptime_s`` so counters are not empty on first view."""
        now = time.time()
        self.started = now - uptime_s
        self.last_tick = now
        self.shares_accepted += int(self.profile.base_ghs * 1e9 / (4096.0 * 4294967296.0) * uptime_s)
        self.shares_rejected += int(self.shares_accepted * 0.006)

    # -- model ----------------------------------------------------------------------------

    def _tick(self) -> None:
        now = time.time()
        dt = max(0.0, now - self.last_tick)
        self.last_tick = now
        if self.paused:
            return
        rate = self.hashrate_ghs() * 1e9
        diff = 4096.0
        shares = rate / (diff * 4294967296.0) * dt
        whole = int(shares) + (1 if self.rng.random() < shares - int(shares) else 0)
        self.shares_accepted += whole
        if whole and self.rng.random() < 0.01:
            self.shares_rejected += 1
        if self.rng.random() < dt * 0.002:
            self.best_diff = max(self.best_diff, self.best_diff * self.rng.uniform(1.01, 1.4))
            self.best_session = max(self.best_session, self.best_session * self.rng.uniform(1.0, 1.5))

    def hashrate_ghs(self) -> float:
        if self.paused:
            return 0.0
        scale = self.settings["frequency"] / self.profile.freq
        wobble = 1 + 0.04 * math.sin(time.time() / 7.0 + hash(self.mac) % 10) + self.rng.uniform(-0.015, 0.015)
        return float(self.profile.base_ghs * scale * wobble)

    def info(self) -> dict[str, Any]:
        self._tick()
        p = self.profile
        hr = self.hashrate_ghs()
        scale = (self.settings["frequency"] / p.freq) * (self.settings["coreVoltage"] / p.core_mv) ** 2
        power = 0.0 if self.paused else p.watts * scale * (1 + self.rng.uniform(-0.01, 0.01))
        temp = 36 + power * p.temp_per_w + self.rng.uniform(-0.5, 0.5)
        up = int(time.time() - self.started)
        d: dict[str, Any] = {
            "ASICModel": p.asic,
            "asicCount": p.asic_count,
            "smallCoreCount": p.small_cores,
            "boardVersion": p.board,
            "version": p.version,
            "axeOSVersion": p.version,
            "idfVersion": "v5.4.1",
            "runningPartition": "ota_0",
            "hostname": self.settings["hostname"],
            "macAddr": self.mac,
            "ssid": "SimWiFi",
            "wifiStatus": "Connected!",
            "wifiRSSI": -55 + self.rng.randrange(-4, 5),
            "ipv4": "127.0.0.1",
            "power": round(power, 3),
            "maxPower": 40,
            "voltage": 5100 + self.rng.randrange(-40, 40),
            "current": round(power / 5.1 * 1000, 1),
            "temp": round(temp, 2),
            "vrTemp": round(temp - 4, 2),
            "hashRate": round(hr, 3),
            "hashRate_1m": round(hr * 0.998, 3),
            "hashRate_10m": round(hr * 1.001, 3),
            "hashRate_1h": round(hr, 3),
            "expectedHashrate": round(p.base_ghs * self.settings["frequency"] / p.freq, 3),
            "errorPercentage": round(self.rng.uniform(0.1, 0.6), 3),
            "frequency": self.settings["frequency"],
            "actualFrequency": float(self.settings["frequency"]) - 0.2,
            "coreVoltage": self.settings["coreVoltage"],
            "coreVoltageActual": self.settings["coreVoltage"] - 3,
            "fanspeed": 0 if self.paused else int(min(100, max(20, (temp - 35) * 2.2))),
            "fanrpm": 0 if self.paused else 3000 + self.rng.randrange(-60, 60),
            "autofanspeed": self.settings["autofanspeed"],
            "manualFanSpeed": self.settings["manualFanSpeed"],
            "temptarget": self.settings["temptarget"],
            "sharesAccepted": self.shares_accepted,
            "sharesRejected": self.shares_rejected,
            "sharesRejectedReasons": [{"message": "Job not found", "count": self.shares_rejected}] if self.shares_rejected else [],
            "bestDiff": self.best_diff,
            "bestSessionDiff": self.best_session,
            "uptimeSeconds": up,
            "freeHeap": 8_000_000 + self.rng.randrange(-5000, 5000),
            "cpuUsage": round(self.rng.uniform(5, 20), 1),
            "isUsingFallbackStratum": 0,
            "poolDifficulty": 4096,
            "responseTime": round(self.rng.uniform(20, 60), 1),
            "stratumURL": self.settings["stratumURL"],
            "stratumPort": self.settings["stratumPort"],
            "stratumUser": self.settings["stratumUser"],
            "fallbackStratumURL": self.settings["fallbackStratumURL"],
            "fallbackStratumPort": self.settings["fallbackStratumPort"],
            "fallbackStratumUser": self.settings["fallbackStratumUser"],
            "blockHeight": 972174,
            "networkDifficulty": 140577680051919.6,
            "blockFound": self.blocks_found,
            "miningPaused": self.paused,
            "overheat_mode": 0,
        }
        if p.device_model:
            d["deviceModel"] = p.device_model
        return d

    # -- http ----------------------------------------------------------------------------

    async def _guard(self, request: Request) -> JSONResponse | None:
        body: Any = None
        if request.method in {"POST", "PATCH"}:
            try:
                body = await request.json()
            except Exception:
                body = None
        self.calls.append((request.method, request.url.path, body))
        if self.fail_next > 0:
            self.fail_next -= 1
            return JSONResponse({"error": "simulated failure"}, status_code=500)
        return None

    def app(self) -> Starlette:
        sim = self

        async def info(request: Request) -> JSONResponse:
            return await sim._guard(request) or JSONResponse(sim.info())

        async def asic(request: Request) -> JSONResponse:
            if (bad := await sim._guard(request)) is not None:
                return bad
            p = sim.profile
            return JSONResponse(
                {
                    "ASICModel": p.asic,
                    "deviceModel": p.device_model or "Unknown",
                    "swarmColor": "purple",
                    "asicCount": p.asic_count,
                    "defaultFrequency": p.freq,
                    "frequencyOptions": list(p.freq_options),
                    "defaultVoltage": p.core_mv,
                    "voltageOptions": list(p.volt_options),
                }
            )

        async def restart(request: Request) -> JSONResponse:
            if (bad := await sim._guard(request)) is not None:
                return bad
            sim.restarts += 1
            sim.started = time.time()
            return JSONResponse({"message": "System will restart shortly."})

        async def identify(request: Request) -> JSONResponse:
            if (bad := await sim._guard(request)) is not None:
                return bad
            sim.identified += 1
            return JSONResponse({"message": "Hi!"})

        async def pause(request: Request) -> JSONResponse:
            if (bad := await sim._guard(request)) is not None:
                return bad
            sim.paused = True
            return JSONResponse({"message": "Mining paused"})

        async def resume(request: Request) -> JSONResponse:
            if (bad := await sim._guard(request)) is not None:
                return bad
            sim.paused = False
            return JSONResponse({"message": "Mining resumed"})

        async def patch(request: Request) -> JSONResponse | PlainTextResponse:
            if (bad := await sim._guard(request)) is not None:
                return bad
            try:
                body = await request.json()
            except Exception:
                return PlainTextResponse("Invalid JSON", status_code=400)
            if not isinstance(body, dict):
                return PlainTextResponse("Invalid settings", status_code=400)
            allowed = set(sim.settings) | {"stratumPassword", "fallbackStratumPassword", "stratumTLS", "fallbackStratumTLS"}
            for k, v in body.items():
                if k not in allowed:
                    return PlainTextResponse(f"Unknown setting {k}", status_code=400)
                sim.settings[k] = v
            return JSONResponse({"status": "success"})

        async def scoreboard(request: Request) -> JSONResponse:
            if (bad := await sim._guard(request)) is not None:
                return bad
            return JSONResponse([{"rank": 1, "difficulty": sim.best_diff, "since": 100, "job_id": "1", "extranonce2": "00", "ntime": 0, "nonce": "0", "version_bits": "0"}])

        async def index(request: Request) -> PlainTextResponse:
            return PlainTextResponse("<html><title>AxeOS</title></html>", media_type="text/html")

        return Starlette(
            routes=[
                Route("/", index),
                Route("/api/system/info", info),
                Route("/api/system/asic", asic),
                Route("/api/system/restart", restart, methods=["POST"]),
                Route("/api/system/identify", identify, methods=["POST"]),
                Route("/api/system/pause", pause, methods=["POST"]),
                Route("/api/system/resume", resume, methods=["POST"]),
                Route("/api/system", patch, methods=["PATCH"]),
                Route("/api/system/scoreboard", scoreboard),
            ]
        )
