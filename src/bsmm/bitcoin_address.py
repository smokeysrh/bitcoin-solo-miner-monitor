"""Tiny, dependency-free Bitcoin address helpers.

Used to (a) validate the payout address a user types in, (b) pull the address out of a stratum
username such as ``bc1q....rig1`` and (c) recognise *our* coinbase payouts when a block is found.
Only mainnet / testnet / regtest formats that Bitcoin Core produces are recognised.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

_B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
_BECH32_CONST = 1
_BECH32M_CONST = 0x2BC830A3
_HRPS = {"bc": "mainnet", "tb": "testnet", "bcrt": "regtest"}

_ADDR_IN_USER = re.compile(
    r"^(?P<addr>(?:bc1|tb1|bcrt1)[0-9a-z]{6,100}|[13mn2][1-9A-HJ-NP-Za-km-z]{25,40})(?:[.\-_ /:](?P<worker>.*))?$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ParsedAddress:
    address: str
    network: str  # mainnet | testnet | regtest
    kind: str  # p2pkh | p2sh | p2wpkh | p2wsh | p2tr | witness_unknown


def _bech32_polymod(values: list[int]) -> int:
    generator = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    chk = 1
    for v in values:
        top = chk >> 25
        chk = (chk & 0x1FFFFFF) << 5 ^ v
        for i in range(5):
            chk ^= generator[i] if ((top >> i) & 1) else 0
    return chk


def _hrp_expand(hrp: str) -> list[int]:
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def _convertbits(data: list[int], frombits: int, tobits: int, pad: bool) -> list[int] | None:
    acc = 0
    bits = 0
    ret: list[int] = []
    maxv = (1 << tobits) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            return None
        acc = (acc << frombits) | value
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret


def _decode_bech32(addr: str) -> ParsedAddress | None:
    if addr.lower() != addr and addr.upper() != addr:
        return None  # mixed case is invalid
    addr = addr.lower()
    pos = addr.rfind("1")
    if pos < 1 or pos + 7 > len(addr) or len(addr) > 90:
        return None
    hrp = addr[:pos]
    if hrp not in _HRPS:
        return None
    try:
        data = [_BECH32_CHARSET.index(c) for c in addr[pos + 1 :]]
    except ValueError:
        return None
    const = _bech32_polymod(_hrp_expand(hrp) + data)
    if const not in (_BECH32_CONST, _BECH32M_CONST):
        return None
    witver = data[0]
    if witver > 16:
        return None
    # v0 must use bech32, v1+ must use bech32m
    if (witver == 0 and const != _BECH32_CONST) or (witver != 0 and const != _BECH32M_CONST):
        return None
    prog = _convertbits(data[1:-6], 5, 8, False)
    if prog is None or not 2 <= len(prog) <= 40:
        return None
    if witver == 0 and len(prog) not in (20, 32):
        return None
    kind = "witness_unknown"
    if witver == 0:
        kind = "p2wpkh" if len(prog) == 20 else "p2wsh"
    elif witver == 1 and len(prog) == 32:
        kind = "p2tr"
    return ParsedAddress(addr, _HRPS[hrp], kind)


def _decode_base58check(addr: str) -> ParsedAddress | None:
    n = 0
    for ch in addr:
        idx = _B58_ALPHABET.find(ch)
        if idx < 0:
            return None
        n = n * 58 + idx
    pad = len(addr) - len(addr.lstrip("1"))
    raw = b"\x00" * pad + n.to_bytes((n.bit_length() + 7) // 8, "big")
    if len(raw) != 25:
        return None

    payload, checksum = raw[:-4], raw[-4:]
    if hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4] != checksum:
        return None
    version = payload[0]
    table = {
        0x00: ("mainnet", "p2pkh"),
        0x05: ("mainnet", "p2sh"),
        0x6F: ("testnet", "p2pkh"),
        0xC4: ("testnet", "p2sh"),
    }
    if version not in table:
        return None
    network, kind = table[version]
    return ParsedAddress(addr, network, kind)


def parse_address(addr: str) -> ParsedAddress | None:
    """Validate ``addr`` (checksum included). ``None`` means invalid."""
    addr = (addr or "").strip()
    if not addr or len(addr) > 100:
        return None
    lowered = addr.lower()
    if lowered.startswith(("bc1", "tb1", "bcrt1")):
        return _decode_bech32(addr)
    return _decode_base58check(addr)


def is_valid_address(addr: str) -> bool:
    return parse_address(addr) is not None


def split_stratum_user(user: str | None) -> tuple[str | None, str | None]:
    """``"bc1q....nerd1"`` -> ``("bc1q....", "nerd1")``.

    The address is returned only if it passes full checksum validation, otherwise ``None``
    (pool accounts that are not addresses, e.g. ``"myaccount.worker1"``, yield ``(None, "worker1")``).
    """
    if not user:
        return None, None
    user = user.strip()
    m = _ADDR_IN_USER.match(user)
    if m:
        cand = m.group("addr")
        worker = m.group("worker") or None
        if parse_address(cand):
            return cand, worker
    if "." in user:
        _, _, worker = user.partition(".")
        return None, worker or None
    return None, None
