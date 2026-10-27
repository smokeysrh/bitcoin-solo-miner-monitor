"""Model identification rules (src/bsmm/drivers/catalog.py).

The rules follow what the device says about itself, in a fixed order, and always return evidence and a
confidence. Cases are adapted from the ``feature/home-miner-identification`` work, which found that the
older heuristics called a Bitaxe Gamma (board 602) a Hex, a Lucky Miner LV08 a Magic Miner and every
cgminer device an Avalon.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bsmm.drivers.catalog import (
    BITAXE_BOARD_FAMILY,
    BITAXE_FAMILIES,
    avalon_model_name,
    identify_axeos,
)
from bsmm.drivers.cgminer import classify

FIX = Path(__file__).parent / "fixtures" / "axeos"


def load(name: str) -> dict:
    return json.loads((FIX / name).read_text())


def axeos(board, asic, chips=None, **extra):
    info = {"ASICModel": asic, "boardVersion": board, "version": "v2.7.1"}
    if chips is not None:
        info["asicCount"] = chips
    info.update(extra)
    return info


# --- real captures ---------------------------------------------------------------------------------


def test_real_gamma_602_is_a_gamma_not_a_hex():
    g = identify_axeos(load("bitaxe_gamma_v2.7.1.json"))
    assert g.model == "Bitaxe Gamma" and g.family == "bitaxe" and g.certain
    assert g.confidence >= 0.9
    assert any("602" in e for e in g.evidence)


@pytest.mark.parametrize("hashrate", [0, 400, 1151, 3000, 9000])
def test_hashrate_never_changes_the_answer(hashrate):
    info = dict(load("bitaxe_gamma_v2.7.1.json"), hashRate=hashrate)
    assert identify_axeos(info).model == "Bitaxe Gamma"


def test_hostname_never_changes_a_stock_board():
    info = dict(load("bitaxe_gamma_v2.7.1.json"), hostname="my-hex-miner")
    assert identify_axeos(info).model == "Bitaxe Gamma"


def test_nerdqaxe_plus_plus_is_kept_verbatim():
    g = identify_axeos(load("nerdqaxe_plusplus_v1.0.30.json"))
    assert g.family == "nerdqaxe" and g.model == "NerdQAxe++"


def test_magic_miner_fixture_still_a_magic_miner():
    g = identify_axeos(load("magicminer_bg02_v1.0.0.json"))
    assert g.family == "magicminer" and g.model == "Magic Miner BG02"


# --- board table (ESP-Miner device_config.h) --------------------------------------------------------


@pytest.mark.parametrize("board", sorted(BITAXE_BOARD_FAMILY))
def test_every_known_board_names_its_family(board):
    fam = BITAXE_FAMILIES[BITAXE_BOARD_FAMILY[board]]
    g = identify_axeos(axeos(board, fam.asic, fam.chips))
    assert g.model == fam.name and g.certain and g.confidence >= 0.9


def test_board_wins_over_a_wrong_chip_count_but_is_flagged():
    g = identify_axeos(axeos("602", "BM1370", 6))
    assert g.model == "Bitaxe Gamma"
    assert g.confidence < 0.9 and not g.certain
    assert any("differs" in e for e in g.evidence)


def test_table_has_no_board_pointing_at_an_unknown_family():
    assert set(BITAXE_BOARD_FAMILY.values()) <= set(BITAXE_FAMILIES)


# --- deviceModel ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("device_model", "expected"),
    [
        ("Ultra", "Bitaxe Ultra"),
        ("Gamma", "Bitaxe Gamma"),
        ("GammaTurbo", "Bitaxe GT"),
        ("gamma turbo", "Bitaxe GT"),
        ("GT", "Bitaxe GT"),
        ("Hex", "Bitaxe Hex"),
        ("SupraHex", "Bitaxe Supra Hex"),
    ],
)
def test_stock_device_model_from_the_asic_endpoint(device_model, expected):
    # stock AxeOS reports deviceModel on /api/system/asic, not /api/system/info
    g = identify_axeos(axeos("999", "BM1370"), {"ASICModel": "BM1370", "deviceModel": device_model, "asicCount": 1})
    assert g.model == expected and g.family == "bitaxe" and g.confidence >= 0.95


def test_conflicting_board_and_device_model_lowers_confidence():
    g = identify_axeos(axeos("302", "BM1370", 1), {"deviceModel": "Gamma"})
    assert g.model == "Bitaxe Gamma" and g.confidence < 0.9


def test_unknown_fork_keeps_its_own_name():
    g = identify_axeos(axeos(None, "BM1370", 8, deviceModel="NerdOctaxe Gamma"))
    assert g.model == "NerdOctaxe Gamma" and g.family == "nerdqaxe"
    other = identify_axeos(axeos(None, "BM1366", 1, deviceModel="Piaxe"))
    assert other.model == "Piaxe" and other.family == "axeos"


# --- fallbacks --------------------------------------------------------------------------------------


def test_unique_chip_layout_when_the_board_is_unknown():
    g = identify_axeos(axeos("9999", "BM1368", 1))
    assert g.model == "Bitaxe Supra" and g.confidence == 0.75 and not g.certain


def test_ambiguous_chip_layout_is_never_guessed():
    g = identify_axeos(axeos("9999", "BM1370", 2))
    assert g.confidence <= 0.6 and "Gamma" not in g.model
    assert set(g.candidates) == {"Bitaxe Gamma Duo", "Bitaxe GT"}


def test_unrecognised_layout_is_not_called_a_gamma():
    g = identify_axeos(axeos("9999", "BM1370", 3))
    assert "Gamma" not in g.model and g.confidence <= 0.5


def test_missing_everything_does_not_crash():
    assert identify_axeos({}).model == "AxeOS miner"
    assert identify_axeos({"ASICModel": "BM1370", "boardVersion": "", "asicCount": "x"}).family == "axeos"


# --- Lucky Miner / Magic Miner ----------------------------------------------------------------------


def test_lucky_miner_lv07_by_layout_is_probable():
    g = identify_axeos(axeos(None, "BM1366", 2, hostname="miner"))
    assert (g.family, g.model) == ("luckyminer", "Lucky Miner LV07")
    assert g.confidence < 0.9 and not g.certain


def test_nine_bm1366_chips_is_a_lucky_lv08_not_a_magic_miner():
    for host in ("lv08", "miner"):
        g = identify_axeos(axeos(None, "BM1366", 9, hostname=host))
        assert (g.family, g.model) == ("luckyminer", "Lucky Miner LV08")


@pytest.mark.parametrize(
    ("hostname", "model"),
    [("lv06", "Lucky Miner LV06"), ("LV-07", "Lucky Miner LV07"), ("luckyminer-lv08", "Lucky Miner LV08")],
)
def test_lucky_miner_hostname_hint(hostname, model):
    assert identify_axeos(axeos(None, "BM1366", None, hostname=hostname)).model == model


def test_a_known_ultra_board_is_not_taken_for_a_lucky_miner():
    assert identify_axeos(axeos("204", "BM1366", 1, hostname="bitaxe")).model == "Bitaxe Ultra"


def test_magic_miner_by_hostname_or_nine_bm1368_chips():
    assert identify_axeos(axeos(None, "BM1368", 3, hostname="MagicMiner-01")).family == "magicminer"
    nine = identify_axeos(axeos(None, "BM1368", 9, hostname="x"))
    assert (nine.family, nine.model) == ("magicminer", "Magic Miner BG02") and not nine.certain


def test_fast_hashing_alone_is_not_a_magic_miner():
    assert identify_axeos(axeos("602", "BM1370", 1, hashRate=9000)).family == "bitaxe"


def test_a_fork_that_reports_its_name_is_not_overruled_by_the_magic_layout():
    assert identify_axeos(axeos(None, "BM1368", 9, deviceModel="SomeFork")).model == "SomeFork"


# --- cgminer / Avalon -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ({"PROD": "Avalonnano", "MODEL": "nano3", "HWTYPE": "PMMv1_X1"}, "Avalon Nano 3"),
        ({"PROD": "Avalonnano", "MODEL": "nano3s"}, "Avalon Nano 3S"),
        ({"PROD": "AvalonMini", "MODEL": "mini3"}, "Avalon Mini 3"),
        ({"PROD": "AvalonQ", "MODEL": "Q"}, "Avalon Q"),
        ({"PROD": "AvalonQ", "MODEL": ""}, "Avalon Q"),
        ({"PROD": "Avalonnano", "MODEL": ""}, "Avalon Nano"),
        ({"PROD": "AvalonMiner 1047", "MODEL": "1047"}, "Avalon 1047"),
        ({"Miner": "Avalon Nano", "CGMiner": "4.10.0"}, "Avalon Nano"),
    ],
)
def test_avalon_models(version, expected):
    family, model = classify(version)
    assert family == "avalon" and model == expected


@pytest.mark.parametrize(
    ("version", "family"),
    [
        ({"PROD": "Antminer S9", "Type": "Antminer S9"}, "antminer"),
        ({"CGMiner": "4.11.1", "API": "3.7", "Type": "Whatsminer M30S"}, "cgminer"),
        ({"PROD": "bosminer", "MODEL": ""}, "braiins"),
    ],
)
def test_other_cgminer_devices_are_never_called_avalon(version, family):
    got, model = classify(version)
    assert got == family and "Avalon" not in model


def test_avalon_model_name_helper_edge_cases():
    assert avalon_model_name("", "", "") == "Avalon"
    assert avalon_model_name("Avalon", "", "") == "Avalon"
