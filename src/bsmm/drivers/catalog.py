"""Knowledge about miner hardware: names, chips, and how to tell boards apart.

Rule of thumb for this module: **never guess from performance.** Hashrate and power move with
settings, so they say nothing about the model. We only use facts the device states about itself
(``deviceModel``, ``minerModel``, ASIC chip + count, hostname), and when those do not settle it we
say so honestly ("AxeOS miner (BM1370 x2)") instead of picking a model name. Users can always
override the model name in the UI.
"""

from __future__ import annotations

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

#: (chip, chip count) -> board name for open-source Bitaxe boards, per the Bitaxe project's lineup.
_BITAXE_BY_CHIP: dict[tuple[str, int], str] = {
    ("BM1397", 1): "Bitaxe Max",
    ("BM1366", 1): "Bitaxe Ultra",
    ("BM1368", 1): "Bitaxe Supra",
    ("BM1370", 1): "Bitaxe Gamma",
    ("BM1370", 2): "Bitaxe GT",
    ("BM1366", 6): "Bitaxe Hex",
    ("BM1368", 6): "Bitaxe Hex",
    ("BM1370", 6): "Bitaxe Hex",
}


@dataclass(frozen=True, slots=True)
class ModelGuess:
    family: str
    model: str
    evidence: tuple[str, ...]
    certain: bool = True


def _s(v: Any) -> str:
    return str(v).strip() if v is not None else ""


def identify_axeos(info: dict[str, Any], asic: dict[str, Any] | None = None) -> ModelGuess:
    """Name an AxeOS-family miner from what it says about itself."""
    hostname = _s(info.get("hostname")).lower()
    device_model = _s(info.get("deviceModel")) or _s((asic or {}).get("deviceModel"))
    miner_model = _s(info.get("minerModel"))
    chip = _s(info.get("ASICModel") or (asic or {}).get("ASICModel")).upper()
    count_raw = info.get("asicCount")
    if count_raw is None and asic:
        count_raw = asic.get("asicCount")
    try:
        count = int(count_raw) if count_raw is not None else 0
    except (TypeError, ValueError):
        count = 0

    if miner_model or "magicminer" in hostname.replace(" ", "").replace("-", "").replace("_", ""):
        label = f"Magic Miner {miner_model}".strip()
        return ModelGuess("magicminer", label, (f"minerModel={miner_model or '-'}", f"hostname={hostname}"))

    if device_model:
        low = device_model.lower()
        if "nerd" in low:
            return ModelGuess("nerdqaxe", device_model, (f"deviceModel={device_model}",))
        if "lucky" in low or "lv0" in low:
            return ModelGuess("luckyminer", device_model, (f"deviceModel={device_model}",))
        name = device_model if low.startswith("bitaxe") else f"Bitaxe {device_model}"
        return ModelGuess("bitaxe", name, (f"deviceModel={device_model}",))

    if str(info.get("initMiner", "")).lower() == "lucky" or hostname.startswith(("lucky", "lv0")):
        return ModelGuess("luckyminer", "Lucky Miner", (f"hostname={hostname}",), certain=False)

    if chip and count:
        board = _BITAXE_BY_CHIP.get((chip, count))
        if board:
            return ModelGuess("bitaxe", board, (f"ASICModel={chip}", f"asicCount={count}"), certain=False)
        return ModelGuess("axeos", f"AxeOS miner ({chip} x{count})", (f"ASICModel={chip}", f"asicCount={count}"), certain=False)
    if chip:
        return ModelGuess("axeos", f"AxeOS miner ({chip})", (f"ASICModel={chip}",), certain=False)
    return ModelGuess("axeos", "AxeOS miner", (), certain=False)


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
