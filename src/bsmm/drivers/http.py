"""HTTP plumbing shared by HTTP-based drivers."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from bsmm.drivers.base import AuthRequired, BadResponse, Unreachable

# Some embedded firmwares print C floats that are not valid JSON (nan / inf). Make them null.
_BAD_TOKENS = re.compile(r"(?<![\"\w])-?(?:nan|inf|infinity)(?![\"\w])", re.IGNORECASE)


def lenient_json_loads(text: str) -> Any:
    """``json.loads`` that survives ``nan``/``inf`` tokens emitted by some ESP32 firmwares."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(_BAD_TOKENS.sub("null", text))


async def request_json(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    timeout: float,
    json_body: Any = None,
    retries: int = 0,
    headers: dict[str, str] | None = None,
    expect_json: bool = True,
) -> Any:
    """Make a request and return the decoded JSON body, translating failures into driver errors.

    ``retries`` is only honoured for idempotent reads (GET); a write is never replayed.
    """
    attempts = 1 + (max(0, retries) if method.upper() == "GET" else 0)
    last: Exception | None = None
    for _ in range(attempts):
        try:
            resp = await client.request(method, url, json=json_body, headers=headers, timeout=timeout)
        except httpx.TimeoutException as e:
            last = Unreachable(f"timed out after {timeout:g}s")
            last.__cause__ = e
            continue
        except httpx.TransportError as e:
            last = Unreachable(_short_transport_error(e))
            last.__cause__ = e
            continue
        if resp.status_code in (401, 403):
            raise AuthRequired(f"HTTP {resp.status_code} (the device refused access)")
        if resp.status_code >= 400:
            raise BadResponse(f"HTTP {resp.status_code} from {method} {_path(url)}")
        if not expect_json:
            return resp.text
        text = resp.text
        if not text.strip():
            return {}
        try:
            return lenient_json_loads(text)
        except json.JSONDecodeError as e:
            raise BadResponse(f"{_path(url)} did not return JSON") from e
    assert last is not None
    raise last


def _path(url: str) -> str:
    m = re.match(r"^[a-z]+://[^/]+(/.*)?$", url)
    return (m.group(1) or "/") if m else url


def _short_transport_error(e: Exception) -> str:
    text = str(e) or e.__class__.__name__
    low = text.lower()
    if "refused" in low:
        return "connection refused"
    if "no route" in low or "unreachable" in low:
        return "no route to host"
    if "name or service" in low or "nodename" in low or "getaddrinfo" in low:
        return "host name not found"
    if "reset" in low:
        return "connection reset"
    return text[:120]
