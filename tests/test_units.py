import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from bsmm.units import (
    format_duration,
    format_hashrate,
    format_odds,
    format_percent,
    format_si,
    parse_difficulty,
    parse_si_number,
    to_float,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("122G", 122e9),
        ("1.25G", 1.25e9),
        ("15.3G", 15.3e9),
        ("51G", 51e9),
        ("4.53M", 4.53e6),
        ("930k", 930e3),
        ("2.1T", 2.1e12),
        ("7.3P", 7.3e15),
        ("1,5G", 1.5e9),
        (" 12 ", 12.0),
        (15300000000, 15.3e9),
        (1.2e11, 1.2e11),
        ("0", 0.0),
        (0, 0.0),
    ],
)
def test_parse_si_number(raw, expected):
    assert parse_si_number(raw) == pytest.approx(expected)


@pytest.mark.parametrize("raw", [None, "", "N/A", "abc", True, False, float("nan"), float("inf"), [], {}])
def test_parse_si_number_rejects_garbage(raw):
    assert parse_si_number(raw) is None


def test_parse_difficulty_alias():
    assert parse_difficulty("122G") == 122e9


def test_to_float_never_raises():
    assert to_float("3.5") == 3.5
    assert to_float(None) is None
    assert to_float("x", default=7.0) == 7.0
    assert to_float(float("nan")) is None


@given(st.floats(min_value=0, max_value=1e24, allow_nan=False, allow_infinity=False))
def test_format_si_is_total(x):
    s = format_si(x, "H/s")
    assert isinstance(s, str) and s


def test_format_hashrate_examples():
    assert format_hashrate(4_726_646_000_000) == "4.73 TH/s"
    assert format_hashrate(12.06e12) == "12.1 TH/s"
    assert format_hashrate(950e6) == "950 MH/s"
    assert format_hashrate(None) == "-"


def test_format_duration():
    assert format_duration(45) == "45s"
    assert format_duration(90_061) == "1d 1h"
    assert format_duration(3_600) == "1h"
    assert format_duration(3_900) == "1h 5m"
    assert format_duration(0.2) == "<1s"
    assert format_duration(1_718 * 365.25 * 86400) == "1,718 years"
    assert format_duration(None) == "-"


def test_format_odds():
    assert format_odds(1 / 1718) == "1 in 1,718"
    assert format_odds(0.25) == "1 in 4.0"
    assert format_odds(1.0) == "certain"
    assert format_odds(0) == "-"
    assert format_odds(None) == "-"
    assert "e+" in format_odds(1e-20)


def test_format_percent():
    assert format_percent(0.5) == "50.00%"
    assert format_percent(0) == "0%"
    assert format_percent(1e-9).endswith("%")
    assert math.isfinite(float(format_percent(0.1234, 1).rstrip("%")))
