# How miners are identified

A wrong model name is worse than no name, so identification only uses what the device says about itself. It never uses hashrate, power or frequency (they move with settings), and it never quietly defaults to a popular model. Every answer comes with a **confidence** and the **evidence** behind it, visible in the miner's page and in `bsmm capture <host>`.

The rules live in [`src/bsmm/drivers/catalog.py`](../src/bsmm/drivers/catalog.py) and are covered by `tests/test_catalog.py`. The approach, the ESP-Miner board table and the Lucky Miner / Avalon rules come from the `feature/home-miner-identification` work on the 0.9 code base, which found that the old guesses called a Bitaxe Gamma (board 602) a Hex, a Lucky Miner LV08 a Magic Miner, and every cgminer device an Avalon.

Support follows firmware and protocol: AxeOS HTTP and compatible cgminer TCP replies. The tables below describe identification rules. Simulator tests exercise generated replies; recorded fixtures exercise captured replies. Physical hardware checks apply to the device and firmware actually checked. A familiar model name alone cannot guarantee every reading or control on another firmware build.

## AxeOS family (Bitaxe, NerdQAxe, Lucky Miner, Magic Miner)

ESP-Miner, the firmware behind AxeOS, picks the device family from the **board version** stored on the device, using [`main/device_config.h`](https://github.com/bitaxeorg/ESP-Miner/blob/master/main/device_config.h). The family fixes the chip and chip count, so the board version is the most reliable fact available.

| Family (`deviceModel`) | Shown as | Chip | Chips | Board versions |
| --- | --- | --- | --- | --- |
| `Max` | Bitaxe Max | BM1397 | 1 | 2.2, 102 |
| `Ultra` | Bitaxe Ultra | BM1366 | 1 | 0.11, 201-205, 207 |
| `Hex` | Bitaxe Hex | BM1366 | 6 | 302, 303 |
| `Supra` | Bitaxe Supra | BM1368 | 1 | 400-403 |
| `Gamma` | Bitaxe Gamma | BM1370 | 1 | 600-603 |
| `GammaDuo` | Bitaxe Gamma Duo | BM1370 | 2 | 650 |
| `SupraHex` | Bitaxe Supra Hex | BM1368 | 6 | 701, 702 |
| `GammaTurbo` | Bitaxe GT (Gamma Turbo) | BM1370 | 2 | 801 |
| `NajaDuo` | Bitaxe Naja Duo | BM1373 | 2 | 1201 |
| `GammaHex` | Bitaxe Gamma Hex | BM1370 | 6 | 1300 |

### Where the facts come from

| Endpoint | Fields used |
| --- | --- |
| `/api/system/info` | `ASICModel`, `boardVersion`, `version`, `hostname`, `macAddr`; forks also add `deviceModel`, `asicCount`, `minerModel` |
| `/api/system/asic` | `deviceModel` (the family name above) and `asicCount` on stock AxeOS |

### Decision order (first match wins)

1. **Magic Miner**: `minerModel` is present, or the hostname contains "magicminer".
2. **Lucky Miner**: the hostname names an LV06, LV07 or LV08 (90%; 75% if the chip count disagrees).
3. **`deviceModel`**: a stock family name gives that Bitaxe (98%). A fork's own name (NerdQAxe+, NerdQAxe++, NerdAxe...) is kept verbatim (95%). If the board table disagrees with the family name, confidence drops to 80%.
4. **`boardVersion`** in the table above gives that Bitaxe (95%). If the chip count disagrees, the board still wins but confidence drops to 80%.
5. **Magic Miner by layout**: 9 or more BM1368 chips, with nothing else to go on (80%, "probable").
6. **Lucky Miner by layout**: BM1366 with 2 or 9 chips matches no stock Bitaxe (65%, "probable").
7. **Chip and chip count** when the pair belongs to exactly one stock family (75%).
8. A pair shared by several families (2x BM1370 is both a Gamma Duo and a GT) is **reported as ambiguous** (60%) with the candidates listed.
9. Anything else is "AxeOS miner (chip xN)" at 50% or less.

Confidence of 90% or more is shown as certain; anything lower says "probably" in the UI.

## cgminer family (Avalon, Antminer, Braiins OS, LuxOS, VNish)

The `version` reply names the product. Avalon home miners are named from `MODEL` / `PROD`: Nano 3, Nano 3S, Mini 3, Q, and full-size machines by number (`Avalon 1047`). Other cgminer devices are named for what they say they are (Antminer, Braiins OS, LuxOS, VNish) and are **never** labelled Avalon.

## Adding or correcting a model

```bash
bsmm capture 192.168.1.50 --out my-miner.json
```

Read-only. It prints what the app thinks the miner is and why, and saves the raw replies with private data removed (Wi-Fi name, MAC, serial, pool URLs and users, wallet addresses). Look the file over, then attach it to an issue or add it as a fixture under `tests/fixtures/` (see [`AGENTS.md`](../AGENTS.md)).

## Known gaps

- **Lucky Miner:** the LV08's 9 chips are not published by the vendor; they come from community firmware that targets that board, so layout matches are labelled probable until confirmed on real hardware.
- **Boards newer than the table** show as "AxeOS miner" until added to `BITAXE_BOARD_FAMILY` in `catalog.py`. Updating that table from ESP-Miner is all that is needed.
- **Restricted API:** an AxeOS device that refuses `/api/system/info` (for example from an unlisted network range) cannot be identified; the scan says it answered but refused.
