"""Read-only capture of one device's replies, with personal data removed.

``bsmm capture 192.168.1.50`` answers two questions: "what does the app think this is, and why?" and
"can I share what this device says so support for it can be added?". It only ever issues GET requests and
the read-only cgminer commands below. Redaction is on by default and works two ways: by key name (Wi-Fi
name, MAC, pool URLs and users, passwords...) and by pattern anywhere in a string (wallet addresses, MAC
addresses). Look the file over before you share it.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx

from bsmm.drivers.cgminer import CgminerDriver, cgminer_call
from bsmm.drivers.registry import probe_host

REDACTED = "<redacted>"
HTTP_PATHS = ("/api/system/info", "/api/system/asic", "/api/system/statistics")
CGMINER_COMMANDS = ("version", "summary", "stats", "devdetails", "pools", "estats")  # all read-only
HTTP_PORTS = (80,)

#: Matched case-insensitively against dictionary keys.
SENSITIVE_KEYS = frozenset(
    {
        "ssid", "wifissid", "wifipass", "wifipassword", "macaddr", "mac", "dna", "hostip", "ip", "ipaddr",
        "user", "username", "password", "pass", "worker",
        "stratumuser", "fallbackstratumuser", "stratumpassword", "fallbackstratumpassword",
        "stratumurl", "fallbackstratumurl", "stratum url", "url", "poolurl",
        "serial", "serialnumber", "sn", "uuid", "apikey", "token",
    }
)

_BTC_ADDRESS = re.compile(r"\b(?:bc1[ac-hj-np-z02-9]{11,87}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b")
_MAC = re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")


def _scrub_text(text: str) -> str:
    return _MAC.sub("AA:BB:CC:00:00:00", _BTC_ADDRESS.sub("<address>", text))


def redact(value: Any) -> Any:
    """A copy of ``value`` with personal data replaced."""
    if isinstance(value, dict):
        return {k: (REDACTED if str(k).lower() in SENSITIVE_KEYS else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return _scrub_text(value)
    return value


async def _get(client: httpx.AsyncClient, host: str, port: int, path: str) -> dict[str, Any]:
    try:
        r = await client.get(f"http://{host}:{port}{path}")
    except httpx.HTTPError as e:
        return {"error": e.__class__.__name__}
    entry: dict[str, Any] = {"status": r.status_code, "content_type": r.headers.get("content-type", "")}
    try:
        entry["json"] = r.json()
    except ValueError:
        entry["text_sample"] = r.text[:2000]
    return entry


async def capture(host: str, *, timeout: float = 4.0, ports: tuple[int, ...] | None = None, scrub: bool = True) -> dict[str, Any]:
    """Probe ``host`` and collect raw replies. Never writes to the device."""
    http_ports = ports if ports else HTTP_PORTS
    async with httpx.AsyncClient(timeout=timeout) as client:
        probes = await probe_host(host, client=client, timeout=timeout)
        result: dict[str, Any] = {
            "host": host,
            "recognised": [
                {
                    "driver": p.info.driver, "family": p.info.family, "model": p.info.model, "port": p.info.port,
                    "confidence": round(p.confidence, 2), "evidence": list(p.evidence),
                    "model_evidence": p.info.extra.get("model_evidence"),
                    "model_confidence": p.info.extra.get("model_confidence"),
                }
                for p in probes
            ],
            "http": {},
            "cgminer": {},
        }
        for port in http_ports:
            result["http"][str(port)] = {path: await _get(client, host, port, path) for path in (*HTTP_PATHS, "/")}
    for port in CgminerDriver.probe_ports:
        replies: dict[str, Any] = {}
        for command in CGMINER_COMMANDS:
            try:
                replies[command] = await cgminer_call(host, port, command, timeout=timeout)
            except Exception as e:
                replies[command] = {"error": f"{e.__class__.__name__}: {e}"[:160]}
                if command == "version":
                    break  # nothing speaks cgminer here; don't wait for five more timeouts
        result["cgminer"][str(port)] = replies
    return redact(result) if scrub else result


def capture_sync(host: str, **kw: Any) -> dict[str, Any]:
    return asyncio.run(capture(host, **kw))
