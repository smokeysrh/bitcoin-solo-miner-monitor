import json
from pathlib import Path

import pytest

from bsmm.bitcoin_address import is_valid_address
from bsmm.drivers.axeos import (
    build_info,
    capabilities_for,
    is_axeos_payload,
    normalize_mac,
    parse_pools,
    parse_system_info,
)
from bsmm.drivers.http import lenient_json_loads
from bsmm.models import Capability

FIX = Path(__file__).parent / "fixtures" / "axeos"


def load(name: str) -> dict:
    return json.loads((FIX / name).read_text())


def test_nerdqaxe_plusplus_live_capture():
    d = load("nerdqaxe_plusplus_v1.0.30.json")
    assert is_axeos_payload(d)
    t = parse_system_info(d, ts=1000.0)
    assert t.hashrate_hs == pytest.approx(4.726646e12)
    assert t.hashrate_10m_hs == pytest.approx(4.726646e12)
    assert t.power_w == pytest.approx(90.875)
    assert t.voltage_in_v == pytest.approx(11.625)
    assert t.current_a == pytest.approx(7.734375)
    assert t.temp_asic_c == pytest.approx(53.3125)
    assert t.temp_vr_c == pytest.approx(56.9375)
    assert t.fan_pct == 73 and t.fan_rpm == 2306
    assert t.frequency_mhz == 600 and t.core_voltage_actual_mv == 1148
    assert t.shares_accepted == 244102 and t.shares_rejected == 76
    assert t.reject_rate_pct == pytest.approx(76 / (244102 + 76) * 100)
    assert t.best_diff == pytest.approx(51e9)
    assert t.efficiency_j_th == pytest.approx(90.875 / 4.726646)
    assert t.pool_connected is True
    assert t.using_fallback is False
    assert t.pool_difficulty == 16384
    assert t.pool_ping_ms == pytest.approx(3.714285714)
    assert t.uptime_s == 3075899
    primary = t.pools[0]
    assert primary.role == "primary" and primary.active is True
    assert primary.url == "192.168.1.10" and primary.port == 2018
    assert primary.address and is_valid_address(primary.address)
    assert primary.worker == "nerdquaxe1"
    fb = t.pools[1]
    assert fb.role == "fallback" and fb.active is False and fb.url == "btc.viabtc.io"
    assert fb.address is None  # an account name, not an address


def test_nerdqaxe_identification():
    d = load("nerdqaxe_plusplus_v1.0.30.json")
    info = build_info("192.168.1.10", 80, d)
    assert info.family == "nerdqaxe"
    assert info.model == "NerdQAxe++"
    assert info.mac and info.mac.startswith("AA:BB:CC:00:00:")
    assert info.asic_model == "BM1370" and info.asic_count == 4
    assert info.firmware == "v1.0.30"
    assert Capability.RESTART in info.capabilities


def test_magic_miner_uses_chip_temp_and_avg_hashrate():
    d = load("magicminer_bg02_v1.0.0.json")
    assert is_axeos_payload(d)
    t = parse_system_info(d)
    assert t.hashrate_hs == pytest.approx(7.314046e12, rel=1e-6)
    assert t.hashrate_avg_hs == pytest.approx(7.101619e12, rel=1e-6)
    assert t.hashrate_10m_hs is None
    # `temp` (38) is the board, `chipTemp` (58.8) is the ASIC
    assert t.temp_asic_c == pytest.approx(58.8125)
    assert t.temp_board_c == 38
    assert t.efficiency_j_th == pytest.approx(149.98 / 7.314, rel=1e-3)
    assert t.best_diff == pytest.approx(122e9) and t.best_session_diff == pytest.approx(15.3e9)
    assert t.pool_connected is None  # this firmware doesn't say; we don't invent it


def test_magic_miner_identification_not_confused_by_asic_count():
    d = load("magicminer_bg02_v1.0.0.json")
    info = build_info("192.168.1.20", 80, d)
    assert info.family == "magicminer"
    assert info.model == "Magic Miner BG02"
    assert info.asic_model == "BM1368" and info.asic_count == 9
    assert info.mac and info.mac.startswith("AA:BB:CC:00:00:")


def test_gamma_old_firmware_rejected_reasons_and_string_diffs():
    d = load("bitaxe_gamma_v2.7.1.json")
    t = parse_system_info(d)
    assert t.rejected_reasons == {"Difficulty too low": 31, "Job not found": 160}
    assert t.best_diff == pytest.approx(1.25e9)
    assert t.best_session_diff == pytest.approx(1e9)
    assert t.wifi_rssi_dbm == -42
    assert t.temp_asic_c == pytest.approx(60.375)
    assert t.pool_difficulty == 2048  # legacy `stratumDiff`
    info = build_info("192.168.1.30", 80, d)
    # board 602 is a Gamma in ESP-Miner's table, regardless of how fast it runs (an older rule called it a Hex)
    assert info.model == "Bitaxe Gamma"
    assert info.extra["model_certain"] is True
    assert info.board_version == "602"


def test_modern_firmware_pools_array_and_new_fields():
    d = load("synthetic_modern_gt.json")
    t = parse_system_info(d)
    assert t.hashrate_1m_hs == pytest.approx(2.2901e12)
    assert t.hashrate_expected_hs == pytest.approx(2.34e12)
    assert t.hw_error_pct == pytest.approx(0.31)
    assert t.temp_asic_c == pytest.approx(61.25)  # the hotter of temp / temp2
    assert t.blocks_found == 0 and t.block_height == 972174
    assert t.network_difficulty == pytest.approx(140577680051919.6)
    assert t.mining_paused is False
    assert [p.role for p in t.pools] == ["primary", "fallback"]
    assert t.pools[0].url == "192.168.1.10"  # scheme stripped
    assert t.pools[0].active and not t.pools[1].active
    info = build_info("192.168.1.60", 80, d)
    assert info.model == "Bitaxe GT" and info.family == "bitaxe"
    caps = set(info.capabilities)
    assert {Capability.PAUSE, Capability.SCOREBOARD, Capability.IDENTIFY, Capability.SET_POOL} <= caps


def test_using_fallback_marks_the_right_pool():
    d = load("synthetic_modern_gt.json")
    d["isUsingFallbackStratum"] = 1
    pools, using = parse_pools(d)
    assert using is True
    assert [p.active for p in pools] == [False, True]


def test_payload_detection():
    assert not is_axeos_payload({"hello": "world"})
    assert not is_axeos_payload([])
    assert not is_axeos_payload({"hashRate": 1})  # needs a second AxeOS marker
    assert is_axeos_payload({"hashRate": 1, "stratumURL": "x"})


def test_garbage_values_do_not_crash_or_lie():
    t = parse_system_info(
        {
            "hashRate": "nope",
            "power": 0,
            "temp": -1,
            "vrTemp": 999,
            "sharesAccepted": None,
            "fanspeed": None,
            "stratumURL": "",
            "bestDiff": "N/A",
        }
    )
    assert t.hashrate_hs is None
    assert t.power_w is None
    assert t.temp_asic_c is None and t.temp_vr_c is None
    assert t.efficiency_j_th is None
    assert t.best_diff is None
    assert t.pools == []


def test_voltage_units_mv_and_v():
    assert parse_system_info({"hashRate": 1, "voltage": 5100}).voltage_in_v == pytest.approx(5.1)
    assert parse_system_info({"hashRate": 1, "voltage": 5.1}).voltage_in_v == pytest.approx(5.1)


def test_lenient_json_handles_nan_tokens():
    assert lenient_json_loads('{"a": nan, "b": -inf, "c": 3}') == {"a": None, "b": None, "c": 3}
    assert lenient_json_loads('{"msg": "nan is fine inside strings"}')["msg"] == "nan is fine inside strings"


def test_normalize_mac():
    assert normalize_mac("aa:bb:cc:2b:42:e4") == "AA:BB:CC:2B:42:E4"
    assert normalize_mac("AA-BB-CC-2B-42-E4") == "AA:BB:CC:2B:42:E4"
    assert normalize_mac("nope") is None
    assert normalize_mac(None) is None


def test_capabilities_are_conservative_for_unknown_firmware():
    caps = capabilities_for({"hashRate": 1, "stratumURL": "x"}, "luckyminer")
    assert caps == [Capability.RESTART]
