"""Unit helpers: parsing what miners send us and formatting numbers for humans.

Internal conventions (everything the engine stores or computes uses these):

* hashrate    -> H/s (float)
* difficulty  -> plain float (``122G`` becomes ``122e9``)
* power       -> watts
* temperature -> degrees Celsius
* efficiency  -> J/TH (identical to W per TH/s)
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable
from typing import Any

# SI prefixes as miners and pools print them (decimal, base 1000).
_SI = {
    "": 1.0,
    "k": 1e3,
    "m": 1e6,  # AxeOS never prints milli, so "m"/"M" both mean mega here.
    "g": 1e9,
    "t": 1e12,
    "p": 1e15,
    "e": 1e18,
    "z": 1e21,
}
_SI_ORDER = [(1e21, "Z"), (1e18, "E"), (1e15, "P"), (1e12, "T"), (1e9, "G"), (1e6, "M"), (1e3, "k")]

_NUM_SUFFIX = re.compile(r"^\s*([+-]?\d+(?:[.,]\d+)?(?:[eE][+-]?\d+)?)\s*([kKmMgGtTpPeEzZ]?)\s*(?:[hH]/?[sS]?)?\s*$")


def parse_si_number(value: Any) -> float | None:
    """Parse ``122G``, ``"1.25M"``, ``15300000000`` or ``"4,5T"`` into a float.

    Returns ``None`` for anything that is not a number (``None``, ``""``, ``"N/A"``,
    booleans). Never raises.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value) if math.isfinite(value) else None
    if not isinstance(value, str):
        return None
    m = _NUM_SUFFIX.match(value)
    if not m:
        return None
    number = float(m.group(1).replace(",", "."))
    prefix = m.group(2).lower()
    result = number * _SI[prefix]
    return result if math.isfinite(result) else None


def parse_difficulty(value: Any) -> float | None:
    """Parse a difficulty as AxeOS/cgminer/pools report it (``"122G"``, ``1.2e11``, ``"15.3M"``)."""
    return parse_si_number(value)


def to_float(value: Any, default: float | None = None) -> float | None:
    """Lenient float conversion that never raises and rejects NaN/inf."""
    if value is None or isinstance(value, bool):
        return default
    try:
        f = float(value)
    except (TypeError, ValueError):
        return default
    return f if math.isfinite(f) else default


def to_int(value: Any, default: int | None = None) -> int | None:
    f = to_float(value)
    if f is None:
        return default
    return int(f)


def format_si(value: float | None, unit: str = "", digits: int = 3) -> str:
    """``4_726_646_000_000`` -> ``4.73 T`` (``unit`` is appended after the prefix)."""
    if value is None or not math.isfinite(value):
        return "-"
    sign = "-" if value < 0 else ""
    v = abs(value)
    for factor, prefix in _SI_ORDER:
        if v >= factor:
            return f"{sign}{_sig(v / factor, digits)} {prefix}{unit}".rstrip()
    return f"{sign}{_sig(v, digits)} {unit}".rstrip()


def format_hashrate(hs: float | None, digits: int = 3) -> str:
    """H/s -> ``4.73 TH/s``."""
    return format_si(hs, "H/s", digits)


def format_difficulty(d: float | None, digits: int = 3) -> str:
    return format_si(d, "", digits)


def format_duration(seconds: float | None, parts: int = 2) -> str:
    """Human duration: ``90061`` -> ``1d 1h``; huge values become years (``1,595 years``)."""
    if seconds is None or not math.isfinite(seconds):
        return "-"
    seconds = max(seconds, 0)
    if seconds < 1:
        return "<1s"
    year = 365.25 * 86400
    if seconds >= 1000 * year:
        return f"{seconds / year:,.0f} years"
    if seconds >= 10 * year:
        return f"{seconds / year:,.1f} years"
    units = [("y", year), ("mo", 30.4375 * 86400), ("d", 86400), ("h", 3600), ("m", 60), ("s", 1)]
    # Start at the first unit that fits, then emit `parts` consecutive units; drop trailing zeros.
    start = next((i for i, (_, size) in enumerate(units) if seconds >= size), len(units) - 1)
    out: list[tuple[str, int]] = []
    remaining = seconds
    for label, size in units[start : start + parts]:
        n = int(remaining // size)
        remaining -= n * size
        out.append((label, n))
    while len(out) > 1 and out[-1][1] == 0:
        out.pop()
    return " ".join(f"{n}{label}" for label, n in out)


def format_odds(probability: float | None) -> str:
    """0.000582 -> ``1 in 1,718``. Handles tiny and huge odds without scientific notation."""
    if probability is None or not math.isfinite(probability) or probability <= 0:
        return "-"
    if probability >= 1:
        return "certain"
    one_in = 1.0 / probability
    if one_in >= 1e15:
        return f"1 in {one_in:.2e}"
    if one_in >= 100:
        return f"1 in {one_in:,.0f}"
    return f"1 in {one_in:,.1f}"


def format_percent(fraction: float | None, digits: int = 2) -> str:
    if fraction is None or not math.isfinite(fraction):
        return "-"
    pct = fraction * 100
    if pct == 0:
        return "0%"
    if abs(pct) < 10 ** (-digits):
        return f"{pct:.1e}%"
    return f"{pct:.{digits}f}%"


def _sig(x: float, digits: int) -> str:
    """Format with ``digits`` significant digits but never more than needed (``4.7`` not ``4.70``)."""
    if x == 0:
        return "0"
    magnitude = math.floor(math.log10(abs(x)))
    decimals = max(0, digits - 1 - magnitude)
    s = f"{x:.{decimals}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def mean(values: Iterable[float]) -> float | None:
    vals = [v for v in values if v is not None and math.isfinite(v)]
    return sum(vals) / len(vals) if vals else None
