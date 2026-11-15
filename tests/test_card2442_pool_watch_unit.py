"""Card #2442: what counts as a change of a miner's pool or payout settings (pure functions, no miner needed).

The comparison keeps only each pool's host, port and payout address. Worker names, passwords, TLS flags and the
active/connected state are not part of it, and spelling differences (case, spaces) are not changes.
"""

from __future__ import annotations

import json

import pytest

from bsmm.bitcoin_address import split_stratum_user
from bsmm.engine.pool_watch import diff, fingerprint, notification_content, shorten_address
from bsmm.models import PoolInfo
from bsmm.sim.axeos import EXAMPLE_ADDR

ADDR_A = EXAMPLE_ADDR
ADDR_B = "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"  # a second valid mainnet address (BIP 173 test vector)
LEGACY_ADDR = "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"  # base58 addresses are case sensitive


def pool(role: str = "primary", url: str | None = "pool.example.net", port: int | None = 3333,
         user: str | None = f"{ADDR_A}.rig1", **extra: object) -> PoolInfo:
    address, worker = split_stratum_user(user)
    return PoolInfo(role=role, url=url, port=port, user=user, address=address, worker=worker, **extra)


def rows(changes) -> list[tuple[str, str, str | None, str | None]]:
    return [(c.slot, c.setting, c.old, c.new) for c in changes]


# --- the fingerprint ---------------------------------------------------------------------------------------------------


def test_fingerprint_keeps_only_host_port_and_payout_address_per_pool():
    assert fingerprint([pool(), pool("fallback", "solo.ckpool.org", 3333, f"{ADDR_B}.rig9")]) == [
        {"slot": "primary", "host": "pool.example.net", "port": 3333, "payout": ADDR_A},
        {"slot": "fallback", "host": "solo.ckpool.org", "port": 3333, "payout": ADDR_B},
    ]


@pytest.mark.parametrize("other_user", [f"{ADDR_A}.rig2", f"{ADDR_A}.", ADDR_A, f"{ADDR_A}-other_worker"])
def test_a_worker_name_only_change_is_not_a_change(other_user):
    assert fingerprint([pool(user=f"{ADDR_A}.rig1")]) == fingerprint([pool(user=other_user)])


def test_flags_and_live_state_are_not_part_of_the_fingerprint():
    quiet = pool()
    busy = pool(active=True, connected=True, difficulty=4096.0, ping_ms=30.0, tls=True, protocol="sv1")
    assert fingerprint([quiet]) == fingerprint([busy])


def test_spelling_differences_are_not_changes():
    plain = fingerprint([pool()])
    assert fingerprint([pool(url="  Pool.Example.NET. ", user=f" {ADDR_A.upper()}.rig1 ")]) == plain


def test_a_base58_address_keeps_its_case():
    [slot] = fingerprint([pool(user=f"{LEGACY_ADDR}.rig1")])
    assert slot["payout"] == LEGACY_ADDR


def test_a_pool_account_that_is_not_an_address_counts_as_the_payout_identity():
    base = fingerprint([pool(user="myaccount.rig1")])
    assert base[0]["payout"] == "myaccount"
    assert base == fingerprint([pool(user="myaccount.rig2")])
    assert base != fingerprint([pool(user="otheraccount.rig1")])


def test_no_pools_gives_an_empty_fingerprint():
    assert fingerprint([]) == []


# --- the difference ----------------------------------------------------------------------------------------------------


def test_identical_fingerprints_have_no_difference():
    assert diff(fingerprint([pool()]), fingerprint([pool(user=f"{ADDR_A}.other")])) == []


@pytest.mark.parametrize(
    ("new_pool", "expected"),
    [
        (pool(url="other.example.net"), [("primary", "pool_address", "pool.example.net", "other.example.net")]),
        (pool(port=4444), [("primary", "pool_port", "3333", "4444")]),
        (pool(user=f"{ADDR_B}.rig1"), [("primary", "payout_address", ADDR_A, ADDR_B)]),
        (pool(url="other.example.net", port=4444, user=f"{ADDR_B}.rig1"),
         [("primary", "pool_address", "pool.example.net", "other.example.net"), ("primary", "pool_port", "3333", "4444"),
          ("primary", "payout_address", ADDR_A, ADDR_B)]),
    ],
)
def test_diff_names_the_setting_and_both_values(new_pool, expected):
    assert rows(diff(fingerprint([pool()]), fingerprint([new_pool]))) == expected


def test_a_fallback_pool_appearing_counts():
    old = fingerprint([pool()])
    new = fingerprint([pool(), pool("fallback", "solo.ckpool.org", 3333, f"{ADDR_B}.x")])
    assert rows(diff(old, new)) == [
        ("fallback", "pool_address", None, "solo.ckpool.org"), ("fallback", "pool_port", None, "3333"),
        ("fallback", "payout_address", None, ADDR_B)]


def test_a_fallback_pool_disappearing_counts():
    old = fingerprint([pool(), pool("fallback", "solo.ckpool.org", 3333, f"{ADDR_B}.x")])
    new = fingerprint([pool()])
    assert rows(diff(old, new)) == [
        ("fallback", "pool_address", "solo.ckpool.org", None), ("fallback", "pool_port", "3333", None),
        ("fallback", "payout_address", ADDR_B, None)]


# --- notification text -------------------------------------------------------------------------------------------------


def test_shorten_address_keeps_the_first_8_and_last_6_characters():
    short = shorten_address(ADDR_A)
    assert short.startswith(ADDR_A[:8]) and short.endswith(ADDR_A[-6:])
    assert len(short) < len(ADDR_A) and ADDR_A not in short


def test_shorten_address_leaves_short_values_alone():
    assert shorten_address("bc1qshort") == "bc1qshort"


def test_notification_text_shortens_payout_addresses_but_not_pool_hosts_or_ports():
    event = {
        "type": "pool_settings_changed", "title": "Garage: pool or payout settings changed", "body": "full text with " + ADDR_B,
        "device_id": "dev_1",
        "data": {"changes": [
            {"slot": "primary", "setting": "payout_address", "old": ADDR_A, "new": ADDR_B},
            {"slot": "primary", "setting": "pool_address", "old": "pool.example.net", "new": "other-pool.example.net"},
            {"slot": "primary", "setting": "pool_port", "old": "3333", "new": "4444"},
        ]},
    }
    title, body, data = notification_content(event)
    text = "\n".join([title, body, json.dumps(data)])
    for address in (ADDR_A, ADDR_B):
        assert address not in text, "the notification must not carry a full address"
        assert address[:8] in text and address[-6:] in text
    assert "other-pool.example.net" in text and "pool.example.net" in text and "4444" in text
    assert "Garage" in title
