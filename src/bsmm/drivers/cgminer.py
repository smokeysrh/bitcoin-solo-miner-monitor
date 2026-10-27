"""cgminer-API family driver (TCP port 4028).

Covers Canaan Avalon (Nano 3 / 3S, Q, Mini 3...), Bitmain Antminer stock firmware, Braiins OS+,
LuxOS, VNish and other cgminer / bmminer derivatives. The API is a tiny JSON-over-TCP protocol:
connect, send ``{"command": "summary"}``, read until the socket closes (or a NUL byte).

This driver is **read-only**. cgminer's write commands (``addpool``, ``ascset``...) differ so much
between firmwares that offering them blindly would be irresponsible; monitoring is what every
variant supports. Wherever a device does not report its own power draw you can set a manual
``power_w`` on the device and efficiency is computed from that (and labelled as manual).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import re
import time
from typing import Any, ClassVar

import httpx

from bsmm.bitcoin_address import split_stratum_user
from bsmm.drivers.base import BadResponse, Driver, DriverError, Unreachable
from bsmm.drivers.catalog import avalon_model_name
from bsmm.models import (
    DeviceInfo,
    PoolInfo,
    ProbeResult,
    Telemetry,
    compute_efficiency,
    compute_reject_rate,
)
from bsmm.units import parse_difficulty, to_float, to_int

_MAX_RESPONSE = 512 * 1024
_BRACKET = re.compile(r"([A-Za-z][A-Za-z0-9_ ]*?)\[([^\]]*)\]")


# --- transport ---------------------------------------------------------------------------------


def parse_cgminer_text(raw: bytes | str) -> dict[str, Any]:
    """Decode a cgminer reply: strip NULs, tolerate trailing garbage after the first JSON value."""
    text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
    text = text.split("\x00", 1)[0].strip()
    if not text:
        raise BadResponse("empty reply")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Some firmwares emit '}{' separated objects or stray bytes; keep the first object.
        try:
            data, _ = json.JSONDecoder().raw_decode(text)
        except json.JSONDecodeError as e:
            raise BadResponse("reply was not JSON") from e
    if not isinstance(data, dict):
        raise BadResponse("reply was not a JSON object")
    return data


async def cgminer_call(
    host: str, port: int, command: str, parameter: str | None = None, *, timeout: float = 5.0
) -> dict[str, Any]:
    payload: dict[str, str] = {"command": command}
    if parameter is not None:
        payload["parameter"] = parameter
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout)
    except TimeoutError as e:
        raise Unreachable(f"timed out connecting to {host}:{port}") from e
    except OSError as e:
        raise Unreachable(f"cannot connect to {host}:{port} ({e.__class__.__name__})") from e
    try:
        writer.write(json.dumps(payload).encode())
        await writer.drain()
        chunks: list[bytes] = []
        total = 0
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                chunk = await asyncio.wait_for(reader.read(8192), remaining)
            except TimeoutError:
                break
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if b"\x00" in chunk or total > _MAX_RESPONSE:
                break
        data = b"".join(chunks)
    except OSError as e:
        raise Unreachable(f"connection to {host}:{port} failed ({e.__class__.__name__})") from e
    finally:
        writer.close()
        with contextlib.suppress(OSError):
            await writer.wait_closed()
    if not data:
        raise BadResponse("the device closed the connection without replying")
    return parse_cgminer_text(data)


# --- helpers over replies --------------------------------------------------------------------------


def status_ok(reply: dict[str, Any]) -> bool:
    st = reply.get("STATUS")
    if isinstance(st, list) and st and isinstance(st[0], dict):
        return str(st[0].get("STATUS", "")).upper() in {"S", "I"}
    if isinstance(st, str):  # Whatsminer style
        return st.upper() in {"S", "I"}
    return False


def section(reply: dict[str, Any], name: str) -> list[dict[str, Any]]:
    val = reply.get(name)
    if isinstance(val, list):
        return [x for x in val if isinstance(x, dict)]
    return []


def parse_bracket_fields(text: str) -> dict[str, str]:
    """Avalon style ``Key[value] Key2[a b c]`` strings into a dict."""
    return {m.group(1).strip(): m.group(2).strip() for m in _BRACKET.finditer(text or "")}


def _first_num(text: str | None) -> float | None:
    if text is None:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(m.group()) if m else None


def _nums(text: str | None) -> list[float]:
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", text or "")]


# --- classification --------------------------------------------------------------------------------


def classify(version: dict[str, Any]) -> tuple[str, str]:
    """(family, model) from a ``version`` reply element."""
    blob = " ".join(f"{k} {v}" for k, v in version.items()).lower()
    prod = str(version.get("PROD", ""))
    model = str(version.get("MODEL", ""))
    mtype = str(version.get("Type", ""))
    if "avalon" in blob or "canaan" in blob:
        legacy = str(version.get("Miner") or mtype)
        return "avalon", avalon_model_name(prod, model, legacy)
    if "bosminer" in blob or "braiins" in blob:
        return "braiins", mtype or "Braiins OS miner"
    if "antminer" in blob or "bmminer" in blob or "bitmain" in blob:
        return "antminer", mtype or "Antminer"
    if "luxminer" in blob or "luxos" in blob:
        return "luxos", mtype or "LuxOS miner"
    if "vnish" in blob:
        return "vnish", mtype or "VNish miner"
    return "cgminer", mtype or prod or "cgminer device"


def _version_element(reply: dict[str, Any]) -> dict[str, Any]:
    v = section(reply, "VERSION")
    return v[0] if v else {}


# --- telemetry parsing ------------------------------------------------------------------------------


def parse_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Fields from a ``summary`` element, in internal units."""
    out: dict[str, Any] = {}

    def mhs(key: str) -> float | None:
        v = to_float(summary.get(key))
        return v * 1e6 if v is not None else None

    def ghs(key: str) -> float | None:
        v = to_float(summary.get(key))
        return v * 1e9 if v is not None else None

    out["hashrate_now"] = mhs("MHS 5s") if "MHS 5s" in summary else ghs("GHS 5s")
    out["hashrate_1m"] = mhs("MHS 1m") if "MHS 1m" in summary else ghs("GHS 1m")
    out["hashrate_avg"] = mhs("MHS av") if "MHS av" in summary else ghs("GHS av")
    out["accepted"] = to_int(summary.get("Accepted"))
    out["rejected"] = to_int(summary.get("Rejected"))
    out["hw_errors"] = to_int(summary.get("Hardware Errors"))
    out["best_share"] = parse_difficulty(summary.get("Best Share"))
    out["elapsed"] = to_int(summary.get("Elapsed"))
    out["found_blocks"] = to_int(summary.get("Found Blocks"))
    hw_pct = to_float(summary.get("Device Hardware%"))
    out["hw_error_pct"] = hw_pct if hw_pct is not None and 0 <= hw_pct <= 100 else None
    return out


def parse_pools(pools: list[dict[str, Any]]) -> list[PoolInfo]:
    result: list[PoolInfo] = []
    ordered = sorted(pools, key=lambda p: to_int(p.get("Priority"), 99) or 0)
    for i, p in enumerate(ordered):
        raw_url = str(p.get("URL") or p.get("Stratum URL") or "")
        if not raw_url:
            continue
        m = re.match(r"^(?:[a-z0-9+]+://)?(?P<host>[^:/]+)(?::(?P<port>\d+))?", raw_url, re.IGNORECASE)
        host = m.group("host") if m else raw_url
        port = int(m.group("port")) if m and m.group("port") else None
        user = p.get("User") if isinstance(p.get("User"), str) else None
        address, worker = split_stratum_user(user)
        status = str(p.get("Status", "")).lower()
        active = bool(p.get("Stratum Active")) if "Stratum Active" in p else None
        result.append(
            PoolInfo(
                role="primary" if i == 0 else "fallback",
                url=host,
                port=port,
                user=user,
                address=address,
                worker=worker,
                active=active,
                connected=(status == "alive") if status else None,
                difficulty=to_float(p.get("Stratum Difficulty")),
                tls=raw_url.lower().startswith(("stratum+ssl", "stratum+tls", "ssl", "tls")) or None,
            )
        )
    if result and not any(p.active for p in result):
        alive = next((p for p in result if p.connected), None)
        if alive:
            alive.active = True
    return result


def parse_avalon_estats(stats: list[dict[str, Any]]) -> dict[str, Any]:
    """Pull temps / fans / frequency / hashrate out of Avalon's ``MM ID<n>`` bracket strings."""
    out: dict[str, Any] = {}
    temp_avg: list[float] = []
    temp_max: list[float] = []
    inlet: list[float] = []
    fan_rpm: list[float] = []
    fan_pct: list[float] = []
    freqs: list[float] = []
    ghs: list[float] = []
    dna: str | None = None
    ver: str | None = None
    workmode: str | None = None
    for element in stats:
        for key, value in element.items():
            if not (isinstance(key, str) and key.startswith("MM ID") and isinstance(value, str)):
                continue
            f = parse_bracket_fields(value)
            if (t := _first_num(f.get("TAvg"))) is not None:
                temp_avg.append(t)
            if (t := _first_num(f.get("TMax"))) is not None:
                temp_max.append(t)
            if (t := _first_num(f.get("Temp"))) is not None:
                inlet.append(t)
            for fk in ("Fan1", "Fan2", "Fan3", "Fan4", "Fan"):
                if (r := _first_num(f.get(fk))) is not None and r > 0:
                    fan_rpm.append(r)
            if (p := _first_num(f.get("FanR"))) is not None:
                fan_pct.append(p)
            if (fr := _first_num(f.get("Freq"))) is not None:
                freqs.append(fr)
            for gk in ("GHSmm", "MGHS"):
                if (g := _first_num(f.get(gk))) is not None:
                    ghs.append(g)
                    break
            dna = dna or f.get("DNA")
            ver = ver or f.get("Ver")
            workmode = workmode or f.get("WORKMODE")
    if temp_avg or temp_max:
        out["temp_asic_c"] = max(temp_avg) if temp_avg else max(temp_max)
    if inlet:
        out["temp_board_c"] = max(inlet)
    if fan_rpm:
        out["fan_rpm"] = max(fan_rpm)
    if fan_pct:
        out["fan_pct"] = max(fan_pct)
    if freqs:
        out["frequency_mhz"] = sum(freqs) / len(freqs)
    if ghs:
        out["hashrate_hs"] = sum(ghs) * 1e9
    if dna:
        out["dna"] = dna
    if ver:
        out["firmware"] = ver
    if workmode:
        out["workmode"] = workmode
    return out


def parse_antminer_stats(stats: list[dict[str, Any]]) -> dict[str, Any]:
    """Temps / fans / rate from Bitmain-style ``stats`` (the second element carries the numbers)."""
    out: dict[str, Any] = {}
    temps: list[float] = []
    fans: list[float] = []
    freqs: list[float] = []
    rate_ghs: float | None = None
    for el in stats:
        for key, value in el.items():
            k = str(key)
            v = to_float(value)
            if v is None:
                continue
            if re.fullmatch(r"temp_chip\d*|temp2_\d+|temp\d+", k) and 0 < v < 150:
                temps.append(v)
            elif re.fullmatch(r"fan\d+", k) and v > 0:
                fans.append(v)
            elif k == "frequency" and v > 0:
                freqs.append(v)
            elif k in ("GHS 5s", "GHS av") and rate_ghs is None:
                rate_ghs = v
            elif k == "total_rateideal" and v > 0:
                out["expected_ghs"] = v
    if temps:
        out["temp_asic_c"] = max(temps)
    if fans:
        out["fan_rpm"] = max(fans)
    if freqs:
        out["frequency_mhz"] = sum(freqs) / len(freqs)
    return out


def build_telemetry(
    summary: dict[str, Any],
    pools: list[dict[str, Any]],
    stats: list[dict[str, Any]],
    *,
    family: str,
    power_override_w: float | None = None,
) -> Telemetry:
    s = parse_summary(summary)
    pool_infos = parse_pools(pools)
    metrics = parse_avalon_estats(stats) if family == "avalon" else parse_antminer_stats(stats)
    hashrate = metrics.get("hashrate_hs") or s["hashrate_now"] or s["hashrate_1m"] or s["hashrate_avg"]
    if family == "avalon" and metrics.get("hashrate_hs"):
        # Avalon's module total is steadier than cgminer's 5 s sample.
        hashrate = metrics["hashrate_hs"]
    power = power_override_w
    source = "manual" if power_override_w is not None else None
    active = next((p for p in pool_infos if p.active), None)
    t = Telemetry(
        online=True,
        hashrate_hs=hashrate,
        hashrate_1m_hs=s["hashrate_1m"],
        hashrate_avg_hs=s["hashrate_avg"],
        hashrate_expected_hs=(metrics.get("expected_ghs") or 0) * 1e9 or None,
        hw_error_pct=s["hw_error_pct"],
        power_w=power,
        power_source=source,
        temp_asic_c=metrics.get("temp_asic_c"),
        temp_board_c=metrics.get("temp_board_c"),
        fan_pct=metrics.get("fan_pct"),
        fan_rpm=metrics.get("fan_rpm"),
        frequency_mhz=metrics.get("frequency_mhz"),
        shares_accepted=s["accepted"],
        shares_rejected=s["rejected"],
        reject_rate_pct=compute_reject_rate(s["accepted"], s["rejected"]),
        best_diff=s["best_share"],
        pools=pool_infos,
        using_fallback=(pool_infos.index(active) > 0) if active in pool_infos else None,
        pool_connected=active.connected if active else None,
        pool_difficulty=active.difficulty if active else None,
        uptime_s=s["elapsed"],
        blocks_found=s["found_blocks"],
    )
    t.efficiency_j_th = compute_efficiency(t.power_w, t.hashrate_hs)
    return t


# --- driver ----------------------------------------------------------------------------------------


class CgminerDriver(Driver):
    name: ClassVar[str] = "cgminer"
    label: ClassVar[str] = "cgminer API (Avalon, Antminer, Braiins OS, LuxOS, VNish...)"
    default_port: ClassVar[int] = 4028
    probe_ports: ClassVar[tuple[int, ...]] = (4028,)

    @property
    def _family(self) -> str:
        return self.info.family if self.info else "cgminer"

    @classmethod
    async def probe(
        cls, host: str, port: int, *, client: httpx.AsyncClient, timeout: float = 4.0
    ) -> ProbeResult | None:
        try:
            ver_reply = await cgminer_call(host, port, "version", timeout=timeout)
        except DriverError:
            return None
        if not status_ok(ver_reply) or not section(ver_reply, "VERSION"):
            return None
        version = _version_element(ver_reply)
        family, model = classify(version)

        extras: dict[str, Any] = {k: str(v) for k, v in version.items() if isinstance(v, str | int | float)}
        serial: str | None = None
        firmware = None
        for key in ("CGMiner", "BMMiner", "BOSminer", "LUXminer", "VERSION", "CGVERSION", "LVERSION"):
            if version.get(key):
                firmware = str(version[key])
                break
        mac = None
        for key in ("MAC", "Mac", "mac"):
            if version.get(key):
                mac = str(version[key]).upper().replace("-", ":")
        if family == "avalon":
            try:
                est = await cgminer_call(host, port, "estats", timeout=timeout)
                serial = parse_avalon_estats(section(est, "STATS")).get("dna")
            except DriverError:
                pass
        info = DeviceInfo(
            driver=cls.name,
            family=family,
            model=model,
            host=host,
            port=port,
            mac=mac if mac and re.fullmatch(r"([0-9A-F]{2}:){5}[0-9A-F]{2}", mac) else None,
            serial=serial,
            firmware=firmware,
            capabilities=[],
            extra={"version": extras, "monitor_only": True},
        )
        telemetry = None
        try:
            driver = cls(host, port, client=client, timeout=timeout, info=info)
            telemetry = await driver.poll()
        except DriverError:
            pass
        evidence = [f"cgminer API 'version' replied on {host}:{port}", f"family={family}", f"model={model}"]
        return ProbeResult(info=info, telemetry=telemetry, confidence=0.9 if family != "cgminer" else 0.7, evidence=evidence)

    async def _call(self, command: str) -> dict[str, Any]:
        """One API call. Overridden by the in-process demo driver."""
        return await cgminer_call(self.host, self.port, command, timeout=self.timeout)

    async def poll(self) -> Telemetry:
        summary_reply = await self._call("summary")
        summary = section(summary_reply, "SUMMARY")
        if not summary:
            raise BadResponse("the device did not return a summary")
        pools: list[dict[str, Any]] = []
        stats: list[dict[str, Any]] = []
        with contextlib.suppress(DriverError):
            pools = section(await self._call("pools"), "POOLS")
        stats_cmd = "estats" if self._family == "avalon" else "stats"
        with contextlib.suppress(DriverError):
            stats = section(await self._call(stats_cmd), "STATS")
        power_override = None
        if self.info and isinstance(self.info.extra.get("power_override_w"), int | float):
            power_override = float(self.info.extra["power_override_w"])
        self.last_raw = {"summary": summary[0], "pools": pools, "stats": stats}
        return build_telemetry(summary[0], pools, stats, family=self._family, power_override_w=power_override)
