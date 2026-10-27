"""Small helpers shared by the route modules."""

from __future__ import annotations

import re
import time

from bsmm.api.errors import bad_request

_RANGE = re.compile(r"^(\d+(?:\.\d+)?)\s*(m|min|h|d|w|mo|y)$", re.IGNORECASE)
_UNITS = {"m": 60, "min": 60, "h": 3600, "d": 86400, "w": 7 * 86400, "mo": 30 * 86400, "y": 365 * 86400}
MAX_RANGE_S = 5 * 365 * 86400


def parse_range(text: str) -> float:
    """``"24h"`` -> 86400.0. Accepts m, h, d, w, mo, y."""
    m = _RANGE.match((text or "").strip())
    if not m:
        raise bad_request(f"{text!r} is not a time range.", "Use a number and a unit, for example 30m, 6h, 24h, 7d, 30d or 1y.")
    seconds = float(m.group(1)) * _UNITS[m.group(2).lower()]
    if seconds <= 0 or seconds > MAX_RANGE_S:
        raise bad_request("That time range is out of bounds.", "Pick between a minute and five years.")
    return seconds


def window(range_: str | None, start: float | None, end: float | None, default: str = "24h") -> tuple[float, float]:
    """(start, end) epoch seconds from either ``range`` or explicit ``start``/``end``."""
    now = time.time()
    if start is not None:
        e = end if end is not None else now
        if e <= start:
            raise bad_request("'end' must be after 'start'.")
        return start, e
    return now - parse_range(range_ or default), now


def csv_list(value: str | None) -> list[str]:
    return [p.strip() for p in (value or "").split(",") if p.strip()]
