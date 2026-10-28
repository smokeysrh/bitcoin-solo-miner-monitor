"""AxeOS / ESP-Miner family driver.

Covers every miner that runs the open-source ESP-Miner HTTP API: Bitaxe (Max, Ultra, Supra, Gamma,
GT, Hex), NerdAxe / NerdQAxe+ / NerdQAxe++, Lucky Miner, Magic Miner and friends. Reference:
https://github.com/bitaxeorg/ESP-Miner/blob/master/main/http_server/openapi.yaml

Reading only needs ``GET /api/system/info`` once per poll. Writes follow the same OpenAPI document.
"""

from __future__ import annotations

import re
import time
from typing import Any, ClassVar

import httpx

from bsmm.bitcoin_address import split_stratum_user
from bsmm.drivers.base import (
    ActionFailed,
    ActionResult,
    BadResponse,
    Driver,
    DriverError,
    TuningOptions,
    Unsupported,
    check_identity,
)
from bsmm.drivers.catalog import identify_axeos
from bsmm.drivers.http import request_json
from bsmm.models import (
    Capability,
    DeviceInfo,
    PoolInfo,
    ProbeResult,
    Telemetry,
    compute_efficiency,
    compute_reject_rate,
)
from bsmm.units import parse_difficulty, to_float, to_int

_GH = 1e9
_MAC_RE = re.compile(r"^[0-9A-Fa-f]{2}([:\-][0-9A-Fa-f]{2}){5}$")


# --- parsing -----------------------------------------------------------------------------------


def is_axeos_payload(data: Any) -> bool:
    """Does this JSON look like an ESP-Miner ``/api/system/info`` response?"""
    if not isinstance(data, dict):
        return False
    has_rate = any(k in data for k in ("hashRate", "hashrate"))
    has_marker = any(k in data for k in ("stratumURL", "ASICModel", "macAddr", "asicCount", "uptimeSeconds"))
    return has_rate and has_marker


def normalize_mac(value: Any) -> str | None:
    if not isinstance(value, str) or not _MAC_RE.match(value.strip()):
        return None
    return value.strip().upper().replace("-", ":")


def _temp(value: Any) -> float | None:
    """Sensor values of 0 / negative / >150 mean 'no sensor' on these firmwares."""
    t = to_float(value)
    if t is None or t <= 0 or t > 150:
        return None
    return t


def _volts(value: Any) -> float | None:
    v = to_float(value)
    if v is None or v <= 0:
        return None
    return v / 1000.0 if v > 100 else v  # firmwares report mV; a few older ones report V


def _amps(value: Any) -> float | None:
    a = to_float(value)
    if a is None or a < 0:
        return None
    return a / 1000.0 if a > 100 else a  # mA normally


def _bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return None


def _gh(value: Any) -> float | None:
    v = to_float(value)
    return v * _GH if v is not None and v >= 0 else None


_SCHEME = re.compile(r"^(?P<scheme>[a-z0-9+]+)://", re.IGNORECASE)


def _split_pool_url(raw: Any, port: Any) -> tuple[str | None, int | None, bool | None]:
    """``stratum+tcp://host:3333`` + port -> (host, port, tls)."""
    if not isinstance(raw, str) or not raw.strip():
        return None, to_int(port), None
    text = raw.strip()
    tls: bool | None = None
    m = _SCHEME.match(text)
    if m:
        scheme = m.group("scheme").lower()
        tls = any(t in scheme for t in ("ssl", "tls", "stratums"))
        text = text[m.end() :]
    text = text.split("/", 1)[0]
    host, _, embedded_port = text.partition(":")
    p = to_int(port) or (to_int(embedded_port) if embedded_port else None)
    return host or None, p, tls


def _pool(role: str, url: Any, port: Any, user: Any, *, tls: Any = None) -> PoolInfo | None:
    host, p, tls_from_url = _split_pool_url(url, port)
    if not host:
        return None
    user_s = user if isinstance(user, str) and user else None
    address, worker = split_stratum_user(user_s)
    tls_flag = _bool(tls) if tls is not None else tls_from_url
    return PoolInfo(role=role, url=host, port=p, user=user_s, address=address, worker=worker, tls=tls_flag)


def parse_pools(data: dict[str, Any]) -> tuple[list[PoolInfo], bool | None]:
    """Primary + fallback pool list and whether the fallback is currently in use."""
    using_fallback = _bool(data.get("isUsingFallbackStratum"))
    pools: list[PoolInfo] = []
    raw_pools = data.get("pools")
    if isinstance(raw_pools, list) and raw_pools:
        primary_i = to_int(data.get("primaryPoolIndex"), 0)
        secondary_i = to_int(data.get("secondaryPoolIndex"), 1)
        for i, p in enumerate(raw_pools):
            if not isinstance(p, dict):
                continue
            role = "primary" if i == primary_i else "fallback" if i == secondary_i else "other"
            built = _pool(role, p.get("stratumURL"), p.get("stratumPort"), p.get("stratumUser"), tls=p.get("stratumTLS"))
            if built:
                pools.append(built)
    else:
        primary = _pool("primary", data.get("stratumURL"), data.get("stratumPort"), data.get("stratumUser"), tls=data.get("stratumTLS"))
        fallback = _pool(
            "fallback",
            data.get("fallbackStratumURL"),
            data.get("fallbackStratumPort"),
            data.get("fallbackStratumUser"),
            tls=data.get("fallbackStratumTLS"),
        )
        pools = [p for p in (primary, fallback) if p]
    active_role = "fallback" if using_fallback else "primary"
    connected = _bool(data.get("isStratumConnected"))
    pool_diff = to_float(data.get("poolDifficulty"))
    if pool_diff is None:
        pool_diff = to_float(data.get("stratumDiff"))
    ping = to_float(data.get("lastpingrtt"))
    if ping is None:
        ping = to_float(data.get("responseTime"))
    for p in pools:
        p.active = p.role == active_role
        if p.active:
            p.connected = connected
            p.difficulty = pool_diff
            p.ping_ms = ping
    return pools, using_fallback


def parse_system_info(data: dict[str, Any], ts: float | None = None) -> Telemetry:
    """Turn an ESP-Miner ``/api/system/info`` payload into normalised telemetry."""
    hashrate = _gh(data.get("hashRate", data.get("hashrate")))
    power = to_float(data.get("power"))
    if power is not None and power <= 0:
        power = None

    # Magic Miner style firmware reports the ASIC temperature as chipTemp and `temp` is the board.
    chip_temp = _temp(data.get("chipTemp"))
    temp_main = _temp(data.get("temp"))
    temp2 = _temp(data.get("temp2"))
    asic_temp: float | None
    board_temp: float | None
    if chip_temp is not None:
        asic_temp = chip_temp
        board_temp = temp_main
    else:
        asic_temp = max((t for t in (temp_main, temp2) if t is not None), default=None)
        board_temp = None

    accepted = to_int(data.get("sharesAccepted"))
    rejected = to_int(data.get("sharesRejected"))
    reasons: dict[str, int] | None = None
    raw_reasons = data.get("sharesRejectedReasons")
    if isinstance(raw_reasons, list):
        reasons = {}
        for r in raw_reasons:
            if isinstance(r, dict) and r.get("message") is not None:
                reasons[str(r["message"])] = to_int(r.get("count"), 0) or 0

    pools, using_fallback = parse_pools(data)
    active = next((p for p in pools if p.active), None)

    fault_parts = [str(data[k]) for k in ("power_fault", "hardware_fault") if data.get(k)]
    err_pct = to_float(data.get("errorPercentage"))

    t = Telemetry(
        ts=ts if ts is not None else time.time(),
        online=True,
        hashrate_hs=hashrate,
        hashrate_1m_hs=_gh(data.get("hashRate_1m")),
        hashrate_10m_hs=_gh(data.get("hashRate_10m")),
        hashrate_1h_hs=_gh(data.get("hashRate_1h")),
        hashrate_1d_hs=_gh(data.get("hashRate_1d")),
        hashrate_avg_hs=_gh(data.get("avgHashRate")),
        hashrate_expected_hs=_gh(data.get("expectedHashrate")),
        hw_error_pct=err_pct if err_pct is not None and 0 <= err_pct <= 100 else None,
        power_w=power,
        voltage_in_v=_volts(data.get("voltage")),
        current_a=_amps(data.get("current")),
        temp_asic_c=asic_temp,
        temp_vr_c=_temp(data.get("vrTemp")),
        temp_board_c=board_temp,
        fan_pct=to_float(data.get("fanspeed")),
        fan_rpm=to_float(data.get("fanrpm")),
        fan2_rpm=to_float(data.get("fan2rpm")),
        frequency_mhz=to_float(data.get("frequency")),
        frequency_actual_mhz=to_float(data.get("actualFrequency")),
        core_voltage_mv=to_float(data.get("coreVoltage")),
        core_voltage_actual_mv=to_float(data.get("coreVoltageActual")),
        shares_accepted=accepted,
        shares_rejected=rejected,
        reject_rate_pct=compute_reject_rate(accepted, rejected),
        best_diff=parse_difficulty(data.get("bestDiff")),
        best_session_diff=parse_difficulty(data.get("bestSessionDiff")),
        rejected_reasons=reasons,
        pools=pools,
        using_fallback=using_fallback,
        pool_connected=active.connected if active else None,
        pool_difficulty=active.difficulty if active else None,
        pool_ping_ms=active.ping_ms if active else None,
        uptime_s=to_int(data.get("uptimeSeconds")),
        firmware=str(data.get("axeOSVersion") or data.get("version") or "") or None,
        wifi_rssi_dbm=to_float(data.get("wifiRSSI")),
        free_heap_bytes=to_int(data.get("freeHeap")),
        cpu_usage_pct=to_float(data.get("cpuUsage")),
        mining_paused=_bool(data.get("miningPaused")),
        fault="; ".join(fault_parts) or None,
        blocks_found=to_int(data.get("blockFound")),
        block_height=to_int(data.get("blockHeight")),
        network_difficulty=parse_difficulty(data.get("networkDifficulty")),
    )
    t.efficiency_j_th = compute_efficiency(t.power_w, t.hashrate_hs)
    return t


def _firmware_at_least(version: str | None, major: int, minor: int) -> bool:
    if not version:
        return False
    m = re.search(r"(\d+)\.(\d+)", version)
    return m is not None and (int(m.group(1)), int(m.group(2))) >= (major, minor)


def capabilities_for(data: dict[str, Any], family: str) -> list[Capability]:
    """Which actions to offer. Conservative: only what the firmware demonstrably supports."""
    caps = [Capability.RESTART]
    official = "idfVersion" in data or "boardVersion" in data or family == "nerdqaxe"
    if official:
        caps += [Capability.SET_POOL, Capability.SET_FAN, Capability.SET_FREQUENCY, Capability.SET_VOLTAGE, Capability.SET_HOSTNAME]
        if _firmware_at_least(str(data.get("version", "")), 2, 5) or family == "nerdqaxe":
            caps.append(Capability.IDENTIFY)
    if "miningPaused" in data:
        caps.append(Capability.PAUSE)
    if "hashRate_1m" in data or "blockHeight" in data:
        caps.append(Capability.SCOREBOARD)
    return caps


def build_info(host: str, port: int, data: dict[str, Any], asic: dict[str, Any] | None = None) -> DeviceInfo:
    guess = identify_axeos(data, asic)
    chip = data.get("ASICModel") or (asic or {}).get("ASICModel")
    count = to_int(data.get("asicCount"))
    if count is None and asic:
        count = to_int(asic.get("asicCount"))
    firmware = data.get("axeOSVersion") or data.get("version")
    extra: dict[str, Any] = {"model_evidence": list(guess.evidence), "model_certain": guess.certain, "model_confidence": guess.confidence}
    for k in ("idfVersion", "runningPartition", "deviceModel", "minerModel", "smallCoreCount", "defaultFrequency"):
        if data.get(k) is not None:
            extra[k] = data[k]
    return DeviceInfo(
        driver=AxeOSDriver.name,
        family=guess.family,
        model=guess.model,
        host=host,
        port=port,
        mac=normalize_mac(data.get("macAddr")),
        hostname=data.get("hostname") if isinstance(data.get("hostname"), str) else None,
        firmware=str(firmware) if firmware else None,
        asic_model=str(chip).upper() if chip else None,
        asic_count=count,
        board_version=str(data["boardVersion"]) if data.get("boardVersion") is not None else None,
        capabilities=capabilities_for(data, guess.family),
        extra=extra,
    )


# --- driver ------------------------------------------------------------------------------------


class AxeOSDriver(Driver):
    name: ClassVar[str] = "axeos"
    label: ClassVar[str] = "AxeOS / ESP-Miner (Bitaxe, NerdQAxe, Lucky Miner, Magic Miner...)"
    default_port: ClassVar[int] = 80
    probe_ports: ClassVar[tuple[int, ...]] = (80,)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._asic_cache: tuple[float, dict[str, Any] | None] | None = None
        self._unsupported: set[str] = set()

    @property
    def base(self) -> str:
        return f"http://{self.host}:{self.port}" if self.port != 80 else f"http://{self.host}"

    # discovery -------------------------------------------------------------------------------

    @classmethod
    async def probe(
        cls, host: str, port: int, *, client: httpx.AsyncClient, timeout: float = 4.0
    ) -> ProbeResult | None:
        base = f"http://{host}:{port}" if port != 80 else f"http://{host}"
        try:
            data = await request_json(client, "GET", f"{base}/api/system/info", timeout=timeout)
        except DriverError:
            return None
        if not is_axeos_payload(data):
            return None
        asic: dict[str, Any] | None
        try:
            asic = await request_json(client, "GET", f"{base}/api/system/asic", timeout=min(timeout, 3.0))
            if not isinstance(asic, dict) or "ASICModel" not in asic:
                asic = None
        except DriverError:
            asic = None
        info = build_info(host, port, data, asic)
        evidence = [f"GET /api/system/info returned an ESP-Miner payload ({len(data)} fields)"]
        evidence += [f"model: {e}" for e in info.extra.get("model_evidence", [])]
        return ProbeResult(info=info, telemetry=parse_system_info(data), confidence=0.98, evidence=evidence)

    # reading ---------------------------------------------------------------------------------

    async def poll(self) -> Telemetry:
        data = await request_json(self.client, "GET", f"{self.base}/api/system/info", timeout=self.timeout, retries=1)
        if not is_axeos_payload(data):
            raise BadResponse("the device answered, but not with ESP-Miner data")
        self.last_raw = data
        if self.info:
            check_identity(self.info, build_info(self.host, self.port, data))
        return parse_system_info(data)

    async def verify_identity(self) -> None:
        await self.poll()

    async def refresh_info(self) -> DeviceInfo | None:
        data = await request_json(self.client, "GET", f"{self.base}/api/system/info", timeout=self.timeout)
        if not is_axeos_payload(data):
            raise BadResponse("the device answered, but not with ESP-Miner data")
        asic = await self._asic()
        observed = build_info(self.host, self.port, data, asic)
        if self.info:
            check_identity(self.info, observed)
        self.info = observed
        return self.info

    async def _asic(self, max_age_s: float = 3600.0) -> dict[str, Any] | None:
        now = time.monotonic()
        if self._asic_cache and now - self._asic_cache[0] < max_age_s:
            return self._asic_cache[1]
        try:
            data = await request_json(self.client, "GET", f"{self.base}/api/system/asic", timeout=min(self.timeout, 4.0))
            asic = data if isinstance(data, dict) and "ASICModel" in data else None
        except DriverError:
            asic = None
        self._asic_cache = (now, asic)
        return asic

    async def tuning_options(self) -> TuningOptions | None:
        asic = await self._asic()
        if not asic:
            return None
        freqs = [int(x) for x in asic.get("frequencyOptions", []) if to_int(x) is not None]
        volts = [int(x) for x in asic.get("voltageOptions", []) if to_int(x) is not None]
        raw = self.last_raw or {}
        return TuningOptions(
            frequency_mhz=freqs,
            core_voltage_mv=volts,
            default_frequency_mhz=to_int(asic.get("defaultFrequency")),
            default_core_voltage_mv=to_int(asic.get("defaultVoltage")),
            max_power_w=to_float(raw.get("maxPower")),
            max_temp_c=to_float(raw.get("overheat_temp")) or 75.0,
        )

    # control ---------------------------------------------------------------------------------

    async def validate_action(self, action: str, params: dict[str, Any]) -> None:
        allowed = {
            "set_pool": {"url", "port", "user", "password", "role", "tls"},
            "set_fan": {"auto", "speed_pct", "temp_target_c"},
            "set_tuning": {"frequency_mhz", "core_voltage_mv"},
        }
        if action not in allowed:
            if action in {"restart", "identify", "pause", "resume"}:
                if params:
                    raise ActionFailed(f"{action} takes no parameters")
                return
            await super().validate_action(action, params)
            return
        if set(params) - allowed[action]:
            raise ActionFailed("unknown action parameters")
        if action == "set_pool":
            self._pool_patch(**params)
        elif action == "set_fan":
            self._fan_patch(**params)
        else:
            await self._tuning_patch(**params)

    async def _write(self, method: str, path: str, body: Any = None, *, what: str) -> ActionResult:
        if what in self._unsupported:
            raise Unsupported(f"{what} is not supported by this firmware")
        try:
            resp = await request_json(self.client, method, f"{self.base}{path}", timeout=self.timeout, json_body=body, expect_json=False)
        except BadResponse as e:
            if "HTTP 404" in str(e) or "HTTP 405" in str(e):
                self._unsupported.add(what)
                raise Unsupported(f"{what} is not supported by this firmware") from e
            raise ActionFailed(str(e)) from e
        return ActionResult(True, f"{what} sent", {"response": (resp or "")[:300]})

    async def restart(self) -> ActionResult:
        return await self._write("POST", "/api/system/restart", None, what="restart")

    async def identify(self) -> ActionResult:
        return await self._write("POST", "/api/system/identify", None, what="identify")

    async def pause(self) -> ActionResult:
        return await self._write("POST", "/api/system/pause", None, what="pause")

    async def resume(self) -> ActionResult:
        return await self._write("POST", "/api/system/resume", None, what="resume")

    async def patch_settings(self, patch: dict[str, Any], *, what: str = "settings") -> ActionResult:
        if not patch:
            raise ActionFailed("nothing to change")
        return await self._write("PATCH", "/api/system", patch, what=what)

    async def set_pool(
        self,
        *,
        url: str,
        port: int,
        user: str,
        password: str = "x",  # noqa: S107 - the conventional stratum password
        role: str = "primary",
        tls: bool | None = None,
    ) -> ActionResult:
        patch = self._pool_patch(url=url, port=port, user=user, password=password, role=role, tls=tls)
        return await self.patch_settings(patch, what=f"set_pool:{role}")

    @staticmethod
    def _pool_patch(*, url: str = "", port: int = 0, user: str = "", password: str = "x",  # noqa: S107
                    role: str = "primary", tls: bool | None = None) -> dict[str, Any]:
        if not isinstance(url, str) or not url.strip() or type(port) is not int or not 1 <= port <= 65535 or not isinstance(user, str) or not user.strip():
            raise ActionFailed("a pool needs a host, a port (1-65535) and a user")
        if role not in ("primary", "fallback") or not isinstance(password, str) or (tls is not None and type(tls) is not bool):
            raise ActionFailed("invalid pool role, password or TLS setting")
        host, embedded_port, _ = _split_pool_url(url, None)
        if not host:
            raise ActionFailed("a pool needs a host, a port (1-65535) and a user")
        prefix = "stratum" if role == "primary" else "fallbackStratum"
        patch: dict[str, Any] = {
            f"{prefix}URL": host,
            f"{prefix}Port": int(port) if port else embedded_port,
            f"{prefix}User": user,
            f"{prefix}Password": password or "x",
        }
        if tls is not None:
            patch[f"{prefix}TLS"] = 1 if tls else 0
        return patch

    async def set_fan(
        self, *, auto: bool | None = None, speed_pct: int | None = None, temp_target_c: int | None = None
    ) -> ActionResult:
        return await self.patch_settings(self._fan_patch(auto=auto, speed_pct=speed_pct, temp_target_c=temp_target_c), what="set_fan")

    @staticmethod
    def _fan_patch(*, auto: bool | None = None, speed_pct: int | None = None,
                   temp_target_c: int | None = None) -> dict[str, Any]:
        patch: dict[str, Any] = {}
        if auto is not None:
            if type(auto) is not bool:
                raise ActionFailed("automatic fan control must be true or false")
            patch["autofanspeed"] = 1 if auto else 0
        if speed_pct is not None:
            if type(speed_pct) is not int or not 0 <= speed_pct <= 100:
                raise ActionFailed("fan speed must be 0-100 %")
            patch["manualFanSpeed"] = int(speed_pct)
        if temp_target_c is not None:
            if type(temp_target_c) is not int or not 30 <= temp_target_c <= 85:
                raise ActionFailed("temperature target must be between 30 and 85 C")
            patch["temptarget"] = int(temp_target_c)
        if not patch:
            raise ActionFailed("nothing to change")
        return patch

    async def set_tuning(
        self, *, frequency_mhz: int | None = None, core_voltage_mv: int | None = None
    ) -> ActionResult:
        """Change ASIC frequency / core voltage, but only to values the device itself lists as valid."""
        patch = await self._tuning_patch(frequency_mhz=frequency_mhz, core_voltage_mv=core_voltage_mv)
        return await self.patch_settings(patch, what="set_tuning")

    async def _tuning_patch(self, *, frequency_mhz: int | None = None,
                            core_voltage_mv: int | None = None) -> dict[str, Any]:
        if frequency_mhz is None and core_voltage_mv is None:
            raise ActionFailed("nothing to change")
        opts = await self.tuning_options()
        if opts is None or not opts.frequency_mhz or not opts.core_voltage_mv:
            raise Unsupported("this firmware does not publish its safe tuning ranges, so tuning is disabled")
        patch: dict[str, Any] = {}
        if frequency_mhz is not None:
            if type(frequency_mhz) is not int or frequency_mhz not in opts.frequency_mhz:
                raise ActionFailed(f"{frequency_mhz} MHz is not one of the device's supported frequencies {opts.frequency_mhz}")
            patch["frequency"] = int(frequency_mhz)
        if core_voltage_mv is not None:
            if type(core_voltage_mv) is not int or core_voltage_mv not in opts.core_voltage_mv:
                raise ActionFailed(f"{core_voltage_mv} mV is not one of the device's supported voltages {opts.core_voltage_mv}")
            patch["coreVoltage"] = int(core_voltage_mv)
        return patch

    async def set_hostname(self, hostname: str) -> ActionResult:
        if not re.fullmatch(r"[A-Za-z0-9-]{1,32}", hostname or ""):
            raise ActionFailed("hostname may only contain letters, digits and '-'")
        return await self.patch_settings({"hostname": hostname}, what="set_hostname")

    async def scoreboard(self) -> list[dict[str, Any]]:
        data = await request_json(self.client, "GET", f"{self.base}/api/system/scoreboard", timeout=self.timeout)
        return data if isinstance(data, list) else []

    async def statistics(self, columns: list[str] | None = None) -> dict[str, Any]:
        path = "/api/system/statistics"
        if columns:
            path += "?columns=" + ",".join(columns)
        data = await request_json(self.client, "GET", f"{self.base}{path}", timeout=self.timeout)
        return data if isinstance(data, dict) else {}
