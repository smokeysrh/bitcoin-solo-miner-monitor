"""Knowledge about miner hardware: names, chips, and how to tell boards apart.

Rule of thumb for this module: **never guess from performance.** Hashrate and power move with
settings, so they say nothing about the model. We only use facts the device states about itself
(``deviceModel``, ``minerModel``, ``boardVersion``, ASIC chip + count, hostname), in this order:

1. Magic Miner: ``minerModel`` / hostname.
2. Lucky Miner: hostname names an LV06 / LV07 / LV08.
3. ``deviceModel``: a stock Bitaxe family name, or a fork's own name (NerdQAxe++, NerdAxe...).
4. ``boardVersion``: the firmware picks the device family from it, so it is authoritative. A 9x BM1368 layout
   with nothing else to go on is a Magic Miner BG02 (probable).
5. Lucky Miner by chip layout (no stock Bitaxe has 2x or 9x BM1366), reported as probable.
6. Chip + chip count, only when that pair belongs to exactly one stock family.
7. Otherwise say so honestly ("AxeOS miner (BM1370 x3)") instead of picking a popular name.

Users can always override the model name in the UI. Every answer carries its evidence and a
confidence so a wrong answer can be diagnosed from one log line. See ``docs/miner-identification.md``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

#: Chip -> marketing generation, used for display only.
ASIC_CHIPS: dict[str, str] = {
    "BM1397": "BM1397 (S17 generation)",
    "BM1366": "BM1366 (S19 XP generation)",
    "BM1368": "BM1368 (S21 generation)",
    "BM1370": "BM1370 (S21 Pro / S21+ generation)",
    "BM1373": "BM1373",
}


@dataclass(frozen=True, slots=True)
class BitaxeFamily:
    id: str  # the firmware's own family name, as reported in ``deviceModel``
    name: str  # what we show
    asic: str
    chips: int


#: Stock Bitaxe families, from ESP-Miner ``main/device_config.h`` (FAMILY_* definitions).
BITAXE_FAMILIES: dict[str, BitaxeFamily] = {
    f.id: f
    for f in (
        BitaxeFamily("Max", "Bitaxe Max", "BM1397", 1),
        BitaxeFamily("Ultra", "Bitaxe Ultra", "BM1366", 1),
        BitaxeFamily("Hex", "Bitaxe Hex", "BM1366", 6),
        BitaxeFamily("Supra", "Bitaxe Supra", "BM1368", 1),
        BitaxeFamily("Gamma", "Bitaxe Gamma", "BM1370", 1),
        BitaxeFamily("GammaDuo", "Bitaxe Gamma Duo", "BM1370", 2),
        BitaxeFamily("SupraHex", "Bitaxe Supra Hex", "BM1368", 6),
        BitaxeFamily("GammaHex", "Bitaxe Gamma Hex", "BM1370", 6),
        BitaxeFamily("GammaTurbo", "Bitaxe GT", "BM1370", 2),  # "Gamma Turbo", sold as the GT
        BitaxeFamily("NajaDuo", "Bitaxe Naja Duo", "BM1373", 2),
    )
}

#: ``boardVersion`` -> family id, from ESP-Miner ``default_configs[]``.
BITAXE_BOARD_FAMILY: dict[str, str] = {
    **dict.fromkeys(("2.2", "102"), "Max"),
    **dict.fromkeys(("0.11", "201", "202", "203", "204", "205", "207"), "Ultra"),
    **dict.fromkeys(("302", "303"), "Hex"),
    **dict.fromkeys(("400", "401", "402", "403"), "Supra"),
    **dict.fromkeys(("600", "601", "602", "603"), "Gamma"),
    "650": "GammaDuo",
    **dict.fromkeys(("701", "702"), "SupraHex"),
    "801": "GammaTurbo",
    "1201": "NajaDuo",
    "1300": "GammaHex",
}


def _norm(value: object) -> str:
    """Lowercase and keep only letters and digits."""
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


_FAMILY_ALIASES: dict[str, str] = {
    **{_norm(f.id): f.id for f in BITAXE_FAMILIES.values()},
    **{_norm(f.name): f.id for f in BITAXE_FAMILIES.values()},
    "gt": "GammaTurbo",
    "bitaxegammaturbo": "GammaTurbo",
}


def _chip_maps() -> tuple[dict[tuple[str, int], str], dict[tuple[str, int], list[str]]]:
    """(chip, count) pairs that name exactly one family, and those shared by several."""
    by_pair: dict[tuple[str, int], list[str]] = {}
    for f in BITAXE_FAMILIES.values():
        by_pair.setdefault((f.asic, f.chips), []).append(f.id)
    unique = {k: v[0] for k, v in by_pair.items() if len(v) == 1}
    shared = {k: v for k, v in by_pair.items() if len(v) > 1}
    return unique, shared


_UNIQUE_PAIR, _SHARED_PAIR = _chip_maps()

#: Lucky Miner LV06 / LV07 / LV08 run AxeOS on BM1366 boards. The LV08's 9 chips are not published by the
#: vendor; the figure comes from community firmware that targets it, so layout matches stay "probable".
_LUCKY_CHIPS = {"LV06": 1, "LV07": 2, "LV08": 9}
_LUCKY_HOSTNAME = re.compile(r"(?<![a-z0-9])lv-?0?([678])(?![0-9])", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class ModelGuess:
    family: str
    model: str
    evidence: tuple[str, ...]
    certain: bool = True
    confidence: float = 0.95
    candidates: tuple[str, ...] = ()


def _s(v: Any) -> str:
    return str(v).strip() if v is not None else ""


def _int(v: Any) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def _guess(family: str, model: str, confidence: float, evidence: list[str], candidates: tuple[str, ...] = ()) -> ModelGuess:
    return ModelGuess(family, model, tuple(evidence), certain=confidence >= 0.9, confidence=confidence, candidates=candidates)


def identify_axeos(info: dict[str, Any], asic: dict[str, Any] | None = None) -> ModelGuess:
    """Name an AxeOS-family miner from what it says about itself."""
    asic = asic or {}
    hostname_raw = _s(info.get("hostname"))
    hostname = hostname_raw.lower()
    device_model = _s(info.get("deviceModel")) or _s(asic.get("deviceModel"))
    miner_model = _s(info.get("minerModel"))
    chip = _s(info.get("ASICModel") or asic.get("ASICModel")).upper()
    count = _int(info.get("asicCount") if info.get("asicCount") is not None else asic.get("asicCount"))
    board = _s(info.get("boardVersion"))
    evidence: list[str] = []

    # 1. Magic Miner
    if miner_model or "magicminer" in _norm(hostname):
        evidence += [f"minerModel={miner_model or '-'}", f"hostname={hostname_raw or '-'}"]
        return _guess("magicminer", f"Magic Miner {miner_model}".strip(), 0.95, evidence)

    # 2. Lucky Miner named in the hostname
    if (m := _LUCKY_HOSTNAME.search(hostname)) is not None:
        lv = f"LV0{m.group(1)}"
        evidence.append(f"hostname '{hostname_raw}' names {lv}")
        conf = 0.9
        if count and count != _LUCKY_CHIPS[lv]:
            evidence.append(f"asicCount {count} differs from the {_LUCKY_CHIPS[lv]} expected for {lv}")
            conf = 0.75
        return _guess("luckyminer", f"Lucky Miner {lv}", conf, evidence)

    # 3. The firmware's own family name
    if device_model:
        low = device_model.lower()
        if "lucky" in low or "lv0" in low:
            return _guess("luckyminer", device_model, 0.95, [f"deviceModel={device_model}"])
        stock = _FAMILY_ALIASES.get(_norm(device_model))
        if stock and "nerd" not in low:
            fam = BITAXE_FAMILIES[stock]
            evidence.append(f"deviceModel={device_model} is a stock {fam.name}")
            conf = 0.98
            board_fam = BITAXE_BOARD_FAMILY.get(board)
            if board_fam and board_fam != stock:
                evidence.append(f"boardVersion {board} belongs to {BITAXE_FAMILIES[board_fam].name}")
                conf = 0.8
            return _guess("bitaxe", fam.name, conf, evidence)
        if "nerd" in low:
            return _guess("nerdqaxe", device_model, 0.95, [f"deviceModel={device_model}"])
        # A fork we do not know by name: keep what it calls itself.
        evidence.append(f"deviceModel={device_model} is not a stock Bitaxe family")
        return _guess("axeos", device_model, 0.9, evidence)

    # 4. Board version: authoritative for stock boards
    if (fam_id := BITAXE_BOARD_FAMILY.get(board)) is not None:
        fam = BITAXE_FAMILIES[fam_id]
        evidence.append(f"boardVersion {board} is a {fam.name} board")
        conf = 0.95
        if count and count != fam.chips:
            evidence.append(f"asicCount {count} differs from the {fam.chips} expected for {fam.name}")
            conf = 0.8
        return _guess("bitaxe", fam.name, conf, evidence)

    # 4b. Magic Miner BG02 by chip layout (only reached when nothing else named the device)
    if chip == "BM1368" and count >= 9:
        evidence.append(f"{count}x BM1368 matches the Magic Miner BG02 layout")
        return _guess("magicminer", "Magic Miner BG02", 0.8, evidence)

    # Older hostname-only hint, kept for firmwares that say "lucky" but not which model
    if _s(info.get("initMiner")).lower() == "lucky" or hostname.startswith(("lucky", "lv0")):
        return _guess("luckyminer", "Lucky Miner", 0.5, [f"hostname={hostname_raw}"])

    # 5. Lucky Miner by chip layout
    if chip == "BM1366" and count in (2, 9):
        lv = "LV07" if count == 2 else "LV08"
        evidence.append(f"{count}x BM1366 matches no stock Bitaxe but fits the {lv}")
        return _guess("luckyminer", f"Lucky Miner {lv}", 0.65, evidence)

    # 6. Chip + chip count, when only one stock family has that pair
    if (fam_id := _UNIQUE_PAIR.get((chip, count))) is not None:
        fam = BITAXE_FAMILIES[fam_id]
        evidence.append(f"{count}x {chip} matches {fam.name} (board '{board or 'n/a'}' is not in the table)")
        return _guess("bitaxe", fam.name, 0.75, evidence)
    if (shared := _SHARED_PAIR.get((chip, count))) is not None:
        names = tuple(BITAXE_FAMILIES[f].name for f in shared)
        evidence.append(f"{count}x {chip} fits several families: {', '.join(names)}")
        return _guess("axeos", f"AxeOS miner ({chip} x{count})", 0.6, evidence, names)

    # 7. Honest fallback
    if chip and count:
        return _guess("axeos", f"AxeOS miner ({chip} x{count})", 0.5, [f"ASICModel={chip}", f"asicCount={count}"])
    if chip:
        return _guess("axeos", f"AxeOS miner ({chip})", 0.4, [f"ASICModel={chip}"])
    return _guess("axeos", "AxeOS miner", 0.3, [])


def expected_hashrate_estimate_hs(info: dict[str, Any]) -> float | None:
    """frequency x small cores x chips. Only a rough health reference; see Telemetry.hashrate_expected_hs."""
    try:
        f = float(info["frequency"])
        cores = float(info["smallCoreCount"])
        n = float(info.get("asicCount") or 1)
    except (KeyError, TypeError, ValueError):
        return None
    if f <= 0 or cores <= 0 or n <= 0:
        return None
    return f * 1e6 * cores * n


# --- cgminer family (Avalon home miners and friends) -------------------------------------------------

_AVALON_HOME = re.compile(r"(nano|mini)(\d*)([a-z]*)")


def avalon_model_name(prod: str, model: str, legacy: str = "") -> str:
    """'Avalon Nano 3', 'Avalon Nano 3S', 'Avalon Mini 3', 'Avalon Q', 'Avalon 1047' from cgminer ``version`` fields."""
    for text in (model, prod, legacy):
        m = _AVALON_HOME.search(_norm(text))
        if m:
            suffix = f" {m.group(2)}{m.group(3).upper()}" if m.group(2) else ""
            return f"Avalon {m.group(1).title()}{suffix}"
    for text in (model, prod, legacy):
        n = _norm(text)
        if n in ("q", "avalonq") or re.fullmatch(r"avalonq\w*", n):
            return "Avalon Q"
    for text in (prod, model, legacy):
        m2 = re.search(r"\b(\d{3,4}[A-Za-z]*)\b", text)  # full-size machines: "AvalonMiner 1047"
        if m2:
            return f"Avalon {m2.group(1).upper()}"
    if "home" in _norm(f"{prod}{model}{legacy}"):
        return "Avalon Home"
    return f"{prod} {model}".strip() or "Avalon"
