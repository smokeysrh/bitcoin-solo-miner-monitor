"""Authentication: optional password for the web UI, scoped API tokens for scripts and AI agents.

Scopes, lowest to highest: ``read`` (look but don't touch), ``control`` (restart / change settings on
miners), ``admin`` (everything incl. managing tokens and passwords). With auth switched off the app
behaves as a single trusted admin, which is what a LAN-only hobby dashboard usually wants; the setup
wizard offers to turn the password on and says why.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections import defaultdict
from dataclasses import dataclass

from bsmm.storage.store import Store

SCOPES = ("read", "control", "admin")
SESSION_TTL_S = 14 * 86400
COOKIE_NAME = "bsmm_session"
PASSWORD_KEY = "auth.password"  # noqa: S105 - the name of a settings row, not a password


@dataclass(frozen=True, slots=True)
class Principal:
    name: str
    scope: str  # read | control | admin
    via: str  # none | session | token | public

    def allows(self, needed: str) -> bool:
        return SCOPES.index(self.scope) >= SCOPES.index(needed)


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt$16384$8$1${salt.hex()}${digest.hex()}"


def verify_password_hash(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    try:
        scheme, n, r, p, salt_hex, digest_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(digest, bytes.fromhex(digest_hex))
    except (ValueError, TypeError):
        return False


class LoginThrottle:
    """After 5 wrong passwords from one address, lock that address out for a growing delay."""

    def __init__(self) -> None:
        self._fails: dict[str, list[float]] = defaultdict(list)

    def locked_for(self, ip: str, now: float | None = None) -> float:
        now = now or time.time()
        if ip not in self._fails:  # a plain lookup must not create an entry for every visitor
            return 0.0
        recent = [t for t in self._fails[ip] if now - t < 900]
        if recent:
            self._fails[ip] = recent
        else:
            del self._fails[ip]
        if len(recent) < 5:
            return 0.0
        wait = min(900.0, 30.0 * float(2 ** (len(recent) - 5)))
        return max(0.0, recent[-1] + wait - now)

    def failed(self, ip: str, now: float | None = None) -> None:
        self._fails[ip].append(now or time.time())
        if len(self._fails) > 2000:  # keep memory bounded under a spray of spoofed addresses
            self._fails.pop(next(iter(self._fails)))

    def ok(self, ip: str) -> None:
        self._fails.pop(ip, None)


class AuthService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.throttle = LoginThrottle()

    async def has_password(self) -> bool:
        return bool(await self.store.kv_get(PASSWORD_KEY))

    async def set_password(self, password: str) -> None:
        if len(password) < 8:
            raise ValueError("Use at least 8 characters.")
        await self.store.kv_set(PASSWORD_KEY, hash_password(password))
        await self.store.delete_all_sessions()  # changing the password logs everyone out

    async def check_password(self, password: str) -> bool:
        return verify_password_hash(password, await self.store.kv_get(PASSWORD_KEY))

    async def login(self, password: str, ip: str, user_agent: str | None) -> str | None:
        wait = self.throttle.locked_for(ip)
        if wait > 0:
            raise PermissionError(f"Too many wrong passwords. Try again in {int(wait) + 1} seconds.")
        if not await self.check_password(password):
            self.throttle.failed(ip)
            return None
        self.throttle.ok(ip)
        return await self.store.create_session(SESSION_TTL_S, user_agent, ip)

    async def principal_from(self, *, bearer: str | None, session: str | None) -> Principal | None:
        if bearer:
            info = await self.store.verify_token(bearer)
            if info:
                return Principal(f"token:{info['name']}", info["scope"], "token")
        if session and await self.store.verify_session(session):
            return Principal("admin", "admin", "session")
        return None
