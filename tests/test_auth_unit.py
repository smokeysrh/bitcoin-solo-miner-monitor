"""Unit tests for ``bsmm.auth``: password hashing, login throttling, principals and the AuthService.

The HTTP flows around login/tokens are covered in ``test_api.py``; these tests pin down the pieces
underneath (the scrypt format, the throttle arithmetic, the scope ladder) so a regression is found
where it happens and not three layers up.
"""

import hashlib
import time

import pytest

from bsmm.auth import (
    SCOPES,
    SESSION_TTL_S,
    AuthService,
    LoginThrottle,
    Principal,
    hash_password,
    verify_password_hash,
)
from bsmm.storage.store import Store

PASSWORD = "correct horse battery"
IP = "192.168.1.77"
T = 1_000_000.0  # an arbitrary "now" for the throttle (never 0: the throttle treats 0 as "unset")


# --- scrypt hashing ----------------------------------------------------------------------------------


def test_hash_has_the_documented_format_and_hides_the_password():
    stored = hash_password(PASSWORD)
    scheme, n, r, p, salt_hex, digest_hex = stored.split("$")
    assert (scheme, n, r, p) == ("scrypt", "16384", "8", "1")
    assert len(bytes.fromhex(salt_hex)) == 16 and len(bytes.fromhex(digest_hex)) == 32
    assert PASSWORD not in stored


def test_round_trip_accepts_only_the_exact_password():
    stored = hash_password(PASSWORD)
    assert verify_password_hash(PASSWORD, stored) is True
    for wrong in ("", "wrong", PASSWORD.upper(), PASSWORD + " ", " " + PASSWORD, PASSWORD[:-1]):
        assert verify_password_hash(wrong, stored) is False, repr(wrong)


def test_unicode_and_empty_passwords_round_trip():
    for pw in ("pässwörd-✓-密码", "", "x" * 500):
        stored = hash_password(pw)
        assert verify_password_hash(pw, stored) is True
    assert verify_password_hash("x", hash_password("")) is False


def test_every_hash_gets_its_own_salt():
    a, b = hash_password(PASSWORD), hash_password(PASSWORD)
    assert a != b
    assert verify_password_hash(PASSWORD, a) and verify_password_hash(PASSWORD, b)


def test_a_fixed_salt_is_deterministic_and_matches_plain_hashlib():
    salt = bytes(range(16))
    first = hash_password(PASSWORD, salt=salt)
    assert first == hash_password(PASSWORD, salt=salt)
    expected = hashlib.scrypt(PASSWORD.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32).hex()
    assert first == f"scrypt$16384$8$1${salt.hex()}${expected}"


def _flip_last_hex_digit(text: str) -> str:
    return text[:-1] + ("0" if text[-1] != "0" else "1")


def test_tampering_with_any_part_of_the_stored_hash_is_detected():
    stored = hash_password(PASSWORD)
    scheme, n, r, p, salt_hex, digest_hex = stored.split("$")
    tampered = [
        "$".join((scheme, n, r, p, salt_hex, _flip_last_hex_digit(digest_hex))),  # digest
        "$".join((scheme, n, r, p, _flip_last_hex_digit(salt_hex), digest_hex)),  # salt
        "$".join((scheme, "8192", r, p, salt_hex, digest_hex)),  # cost parameter
        "$".join((scheme, n, "4", p, salt_hex, digest_hex)),
        "$".join((scheme, n, r, "2", salt_hex, digest_hex)),
    ]
    for t in tampered:
        assert verify_password_hash(PASSWORD, t) is False, t
    assert verify_password_hash(PASSWORD, stored) is True  # the untouched original still works


@pytest.mark.parametrize(
    "stored",
    [
        None,
        "",
        "plaintext-password",
        "scrypt$",
        "scrypt$16384$8$1$00",  # too few parts
        "scrypt$16384$8$1$00$00$extra",  # too many parts
        "scrypt$16384$8$1$not-hex$not-hex",
        "scrypt$abc$8$1$00$00",  # cost is not a number
        "bcrypt$16384$8$1$" + "00" * 16 + "$" + "00" * 32,  # unknown scheme
        "scrypt$1000$8$1$" + "00" * 16 + "$" + "00" * 32,  # n is not a power of two
        "scrypt$1073741824$8$1$" + "00" * 16 + "$" + "00" * 32,  # absurd memory cost is refused, not attempted
    ],
)
def test_malformed_stored_hashes_fail_closed_without_raising(stored):
    assert verify_password_hash(PASSWORD, stored) is False


# --- login throttle ----------------------------------------------------------------------------------


def _fail(throttle: LoginThrottle, times: int, ip: str = IP, at: float = T) -> None:
    for _ in range(times):
        throttle.failed(ip, at)


def test_fewer_than_five_failures_never_lock():
    th = LoginThrottle()
    assert th.locked_for(IP, T) == 0.0
    _fail(th, 4)
    assert th.locked_for(IP, T) == 0.0


def test_the_fifth_failure_locks_for_thirty_seconds_then_releases():
    th = LoginThrottle()
    _fail(th, 5)
    assert th.locked_for(IP, T) == pytest.approx(30.0)
    assert th.locked_for(IP, T + 10) == pytest.approx(20.0)
    assert th.locked_for(IP, T + 29.5) == pytest.approx(0.5)
    assert th.locked_for(IP, T + 30) == 0.0


@pytest.mark.parametrize(
    ("failures", "lock_s"),
    [(5, 30), (6, 60), (7, 120), (8, 240), (9, 480), (10, 900), (11, 900), (15, 900)],
)
def test_lockout_doubles_with_every_further_failure_up_to_fifteen_minutes(failures, lock_s):
    th = LoginThrottle()
    _fail(th, failures)
    assert th.locked_for(IP, T) == pytest.approx(lock_s)


def test_lockout_counts_from_the_most_recent_failure():
    th = LoginThrottle()
    for i in range(5):
        th.failed(IP, T + i)  # the last one lands at T + 4
    assert th.locked_for(IP, T + 4) == pytest.approx(30.0)
    th.failed(IP, T + 20)  # a sixth try that ignored the lock: 60 s, measured from T + 20
    assert th.locked_for(IP, T + 20) == pytest.approx(60.0)
    assert th.locked_for(IP, T + 79) == pytest.approx(1.0)
    assert th.locked_for(IP, T + 80) == 0.0


def test_failures_are_forgotten_after_fifteen_minutes():
    th = LoginThrottle()
    _fail(th, 10)  # 900 s lockout
    assert th.locked_for(IP, T + 899) == pytest.approx(1.0)
    assert th.locked_for(IP, T + 900) == 0.0
    assert IP not in th._fails  # pruned, not just ignored
    _fail(th, 1, at=T + 901)
    assert th.locked_for(IP, T + 901) == 0.0  # a clean slate: one failure is just one failure


def test_merely_checking_an_address_does_not_remember_it():
    th = LoginThrottle()
    for i in range(50):
        assert th.locked_for(f"10.1.0.{i}", T) == 0.0  # visitors who never failed a login
    assert th._fails == {}


def test_success_resets_the_counter():
    th = LoginThrottle()
    _fail(th, 5)
    assert th.locked_for(IP, T) > 0
    th.ok(IP)
    assert th.locked_for(IP, T) == 0.0
    _fail(th, 4)  # counting starts again from zero
    assert th.locked_for(IP, T) == 0.0
    th.ok("never-failed")  # resetting an unknown address is harmless


def test_addresses_are_throttled_independently():
    th = LoginThrottle()
    _fail(th, 6, ip="10.0.0.1")
    assert th.locked_for("10.0.0.1", T) > 0
    assert th.locked_for("10.0.0.2", T) == 0.0
    _fail(th, 4, ip="10.0.0.2")
    assert th.locked_for("10.0.0.2", T) == 0.0


def test_the_clock_defaults_to_now():
    th = LoginThrottle()
    for _ in range(5):
        th.failed(IP)
    assert 0 < th.locked_for(IP) <= 30.0
    assert th.locked_for(IP, time.time() + 31) == 0.0


def test_memory_stays_bounded_under_a_spray_of_spoofed_addresses():
    th = LoginThrottle()
    _fail(th, 5, ip="the-first-victim")
    assert th.locked_for("the-first-victim", T) > 0
    for i in range(2600):
        th.failed(f"10.{i // 256}.{i % 256}.9", T)
    assert len(th._fails) <= 2000
    assert th.locked_for("the-first-victim", T) == 0.0  # the oldest entry was evicted to make room
    assert th._fails["10.10.0.9"] == [T]  # the newest entries are kept


# --- principals / scopes -----------------------------------------------------------------------------


def test_scopes_are_ordered_from_least_to_most_powerful():
    assert SCOPES == ("read", "control", "admin")


@pytest.mark.parametrize(
    ("scope", "needed", "allowed"),
    [
        ("read", "read", True), ("read", "control", False), ("read", "admin", False),
        ("control", "read", True), ("control", "control", True), ("control", "admin", False),
        ("admin", "read", True), ("admin", "control", True), ("admin", "admin", True),
    ],
)
def test_principal_allows_follows_the_scope_ladder(scope, needed, allowed):
    assert Principal("someone", scope, "token").allows(needed) is allowed


def test_how_you_authenticated_does_not_change_what_you_may_do():
    for via in ("none", "session", "token", "public"):
        assert Principal("x", "read", via).allows("control") is False
        assert Principal("x", "admin", via).allows("admin") is True


def test_an_unknown_scope_never_grants_access():
    for principal, needed in ((Principal("x", "root", "token"), "read"), (Principal("x", "admin", "token"), "superuser")):
        try:
            granted = principal.allows(needed)
        except ValueError:
            granted = False  # failing loudly is as safe as saying no
        assert granted is False


def test_principals_are_immutable():
    p = Principal("x", "read", "token")
    with pytest.raises(AttributeError):
        p.scope = "admin"  # type: ignore[misc]


# --- AuthService -------------------------------------------------------------------------------------


@pytest.fixture
async def store():
    s = await Store.open_memory()
    yield s
    await s.close()


@pytest.fixture
async def auth(store):
    return AuthService(store)


async def test_set_password_validates_length_and_stores_only_a_hash(auth, store):
    assert await auth.has_password() is False
    with pytest.raises(ValueError, match="at least 8"):
        await auth.set_password("short")
    assert await auth.has_password() is False
    await auth.set_password(PASSWORD)
    assert await auth.has_password() is True
    stored = await store.kv_get("auth.password")
    assert stored.startswith("scrypt$") and PASSWORD not in stored
    assert await auth.check_password(PASSWORD) is True
    assert await auth.check_password("nope nope nope") is False


async def test_login_issues_a_session_that_resolves_to_an_admin(auth, store):
    await auth.set_password(PASSWORD)
    sid = await auth.login(PASSWORD, IP, "pytest")
    assert sid and await store.verify_session(sid)
    who = await auth.principal_from(bearer=None, session=sid)
    assert who == Principal("admin", "admin", "session")


async def test_login_without_a_password_set_or_with_a_wrong_one_returns_none(auth):
    assert await auth.login("anything at all", IP, None) is None  # nothing configured yet
    await auth.set_password(PASSWORD)
    assert await auth.login("wrong password", IP, None) is None


async def test_five_wrong_passwords_lock_the_address_even_for_the_right_one(auth):
    await auth.set_password(PASSWORD)
    for _ in range(5):
        assert await auth.login("wrong password", IP, None) is None
    with pytest.raises(PermissionError, match=r"Too many wrong passwords\. Try again in \d+ seconds"):
        await auth.login(PASSWORD, IP, None)
    assert await auth.login(PASSWORD, "192.168.1.78", None)  # somebody else is unaffected


async def test_a_successful_login_clears_earlier_failures(auth):
    await auth.set_password(PASSWORD)
    for _ in range(4):
        await auth.login("wrong password", IP, None)
    assert await auth.login(PASSWORD, IP, None)
    for _ in range(4):  # would be the 8th failure overall if the counter had not been reset
        assert await auth.login("wrong password", IP, None) is None
    assert await auth.login(PASSWORD, IP, None)  # still not locked


async def test_changing_the_password_logs_everyone_out(auth, store):
    await auth.set_password(PASSWORD)
    sid = await auth.login(PASSWORD, IP, None)
    assert await auth.principal_from(bearer=None, session=sid) is not None
    await auth.set_password("a brand new password")
    assert await auth.principal_from(bearer=None, session=sid) is None
    assert await auth.check_password(PASSWORD) is False
    assert await auth.check_password("a brand new password") is True


async def test_bearer_tokens_resolve_with_their_own_scope(auth, store):
    tid, token = await store.create_token("grafana", "read")
    who = await auth.principal_from(bearer=token, session=None)
    assert who == Principal("token:grafana", "read", "token")
    assert who.allows("read") and not who.allows("control")
    [row] = await store.list_tokens()
    assert row["id"] == tid and row["last_used_at"] is not None  # using a token is recorded


async def test_bad_expired_and_revoked_tokens_are_refused(auth, store):
    assert await auth.principal_from(bearer="bsmm_not-a-real-token", session=None) is None
    _, expired = await store.create_token("old", "admin", expires_at=time.time() - 5)
    assert await auth.principal_from(bearer=expired, session=None) is None
    tid, revoked = await store.create_token("gone", "admin")
    assert await auth.principal_from(bearer=revoked, session=None) is not None
    await store.delete_token(tid)
    assert await auth.principal_from(bearer=revoked, session=None) is None


async def test_a_bad_token_falls_back_to_a_valid_session_and_neither_means_nobody(auth, store):
    await auth.set_password(PASSWORD)
    sid = await auth.login(PASSWORD, IP, None)
    assert (await auth.principal_from(bearer="bsmm_garbage", session=sid)).via == "session"
    assert await auth.principal_from(bearer="bsmm_garbage", session="garbage") is None
    assert await auth.principal_from(bearer=None, session=None) is None


async def test_an_expired_session_does_not_authenticate(auth, store):
    sid = await store.create_session(-1, "pytest", IP)  # already past its expiry
    assert await auth.principal_from(bearer=None, session=sid) is None
    live = await store.create_session(SESSION_TTL_S, "pytest", IP)
    assert (await auth.principal_from(bearer=None, session=live)).scope == "admin"
    assert SESSION_TTL_S == 14 * 86400
