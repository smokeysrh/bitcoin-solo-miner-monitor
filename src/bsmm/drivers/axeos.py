"""AxeOS / ESP-Miner family driver.

Covers every miner that runs the open-source ESP-Miner HTTP API: Bitaxe (Max, Ultra, Supra, Gamma,
GT, Hex), NerdAxe / NerdQAxe+ / NerdQAxe++, Lucky Miner, Magic Miner and friends. Reference:
https://github.com/bitaxeorg/ESP-Miner/blob/master/main/http_server/openapi.yaml

Reading only needs ``GET /api/system/info`` once per poll. This driver is read-only: it sends GET requests and nothing else.
"""

from __future__ import annotations

import re
import time
from typing import Any, ClassVar

import httpx

from bsmm.bitcoin_address import split_stratum_user
from bsmm.drivers.base import (
    BadResponse,
    Driver,
    DriverError,
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
_MAC_GROUP_BIT = 0x01


# --- parsing -----------------------------------------------------------------------------------


def is_axeos_payload(data: Any) -> bool:
    """Does this JSON look like an ESP-Miner ``/api/system/info`` response?"""
    if not isinstance(data, dict):
        return False
    has_rate = any(k in data for k in ("hashRate", "hashrate"))
    has_marker = any(k in data for k in ("stratumURL", "ASICModel", "macAddr", "asicCount", "uptimeSeconds"))
    return has_rate and has_marker


def normalize_mac(value: Any) -> str | None:
    """Return an individual MAC, never zero or group/broadcast firmware placeholders."""
    if not isinstance(value, str) or not _MAC_RE.match(value.strip()):
        return None
    mac = value.strip().upper().replace("-", ":")
    if mac == "00:00:00:00:00:00" or int(mac[:2], 16) & _MAC_GROUP_BIT:
        return None
    return mac  # Locally administered unicast addresses remain distinct identities.


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


def capabilities_for(data: dict[str, Any]) -> list[Capability]:
    """Read-only features this firmware reports."""
    caps: list[Capability] = []
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
        capabilities=capabilities_for(data),
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

    def _check_identity(self, observed: DeviceInfo) -> None:
        if self.info:
            # Older releases could persist unusable MACs. Compare a copy, never rewrite them.
            expected = self.info.model_copy(update={"mac": normalize_mac(self.info.mac)})
            check_identity(expected, observed)

    async def poll(self) -> Telemetry:
        data = await request_json(self.client, "GET", f"{self.base}/api/system/info", timeout=self.timeout, retries=1)
        if not is_axeos_payload(data):
            raise BadResponse("the device answered, but not with ESP-Miner data")
        self.last_raw = data
        self._check_identity(build_info(self.host, self.port, data))
        return parse_system_info(data)

    async def refresh_info(self) -> DeviceInfo | None:
        data = await request_json(self.client, "GET", f"{self.base}/api/system/info", timeout=self.timeout)
        if not is_axeos_payload(data):
            raise BadResponse("the device answered, but not with ESP-Miner data")
        asic = await self._asic()
        observed = build_info(self.host, self.port, data, asic)
        self._check_identity(observed)
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

    async def scoreboard(self) -> list[dict[str, Any]]:
        data = await request_json(self.client, "GET", f"{self.base}/api/system/scoreboard", timeout=self.timeout)
        return data if isinstance(data, list) else []

    async def statistics(self, columns: list[str] | None = None) -> dict[str, Any]:
        path = "/api/system/statistics"
        if columns:
            path += "?columns=" + ",".join(columns)
        data = await request_json(self.client, "GET", f"{self.base}{path}", timeout=self.timeout)
        return data if isinstance(data, dict) else {}
