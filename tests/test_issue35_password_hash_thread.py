"""Issue #35: scrypt password hashing must not run on the event loop.

A controlled stand-in for ``hashlib.scrypt`` blocks until the test releases it. The test coroutine
is the only thing that can release it, so if the hash runs on the event-loop thread the loop cannot
run the test, the stand-in times out (``stalled``) and the test fails. Hashing off the loop lets the
test run while the hash is in flight. Results still come from the real scrypt.
"""

import asyncio
import hashlib
import threading
import time
from collections.abc import AsyncIterator, Callable
from typing import Any

import pytest

from bsmm.auth import AuthService
from bsmm.storage.store import Store

PASSWORD = "correct horse battery"
STALL_TIMEOUT_S = 1.0  # how long a blocked stand-in waits for the event loop to release it
POLL_DEADLINE_S = 5.0
POLL_STEP_S = 0.005
MAX_SIMULTANEOUS_HASHES = 4  # "small": the service may run at most this many hashes at once
BURST = 8  # more concurrent checks than that bound


class ControlledScrypt:
    """Blocks each call until ``release`` is set, records where and how many ran, then hashes for real."""

    def __init__(self, real: Callable[..., bytes], loop_thread: int) -> None:
        self._real = real
        self._loop_thread = loop_thread
        self._lock = threading.Lock()
        self.release = threading.Event()
        self.calls = 0
        self.active = 0
        self.max_active = 0
        self.on_loop_thread = False
        self.stalled = False  # nobody released a call in time: the loop was blocked

    def reset(self) -> None:
        with self._lock:
            self.calls = 0
            self.max_active = 0

    def __call__(self, *args: Any, **kwargs: Any) -> bytes:
        with self._lock:
            self.calls += 1
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            if threading.get_ident() == self._loop_thread:
                self.on_loop_thread = True
        try:
            if not self.release.wait(STALL_TIMEOUT_S):
                self.stalled = True
                self.release.set()  # let the rest of the test fail quickly instead of waiting again
            return self._real(*args, **kwargs)
        finally:
            with self._lock:
                self.active -= 1


async def wait_until(condition: Callable[[], bool]) -> None:
    deadline = time.monotonic() + POLL_DEADLINE_S
    while not condition():
        assert time.monotonic() < deadline, "condition never became true"
        await asyncio.sleep(POLL_STEP_S)


@pytest.fixture
async def store() -> AsyncIterator[Store]:
    s = await Store.open_memory()
    yield s
    await s.close()


@pytest.fixture
async def auth(store: Store) -> AuthService:
    return AuthService(store)


@pytest.fixture
def controlled_scrypt(monkeypatch: pytest.MonkeyPatch) -> ControlledScrypt:
    fake = ControlledScrypt(hashlib.scrypt, threading.get_ident())
    monkeypatch.setattr(hashlib, "scrypt", fake)
    return fake


async def test_password_check_leaves_the_event_loop_free(auth: AuthService, controlled_scrypt: ControlledScrypt) -> None:
    controlled_scrypt.release.set()
    await auth.set_password(PASSWORD)  # store a real hash first
    controlled_scrypt.release.clear()
    controlled_scrypt.reset()

    check = asyncio.create_task(auth.check_password(PASSWORD))
    await wait_until(lambda: controlled_scrypt.calls >= 1)
    controlled_scrypt.release.set()  # only reachable in time if the loop kept running during the hash

    assert await check is True
    assert controlled_scrypt.stalled is False
    assert controlled_scrypt.on_loop_thread is False


async def test_setting_a_password_leaves_the_event_loop_free(auth: AuthService, controlled_scrypt: ControlledScrypt) -> None:
    setting = asyncio.create_task(auth.set_password(PASSWORD))
    await wait_until(lambda: controlled_scrypt.calls >= 1)
    controlled_scrypt.release.set()
    await setting

    assert controlled_scrypt.stalled is False
    assert controlled_scrypt.on_loop_thread is False
    assert await auth.check_password(PASSWORD) is True


async def test_simultaneous_checks_are_bounded_and_cancelled_waiters_never_hash(
    auth: AuthService, controlled_scrypt: ControlledScrypt
) -> None:
    controlled_scrypt.release.set()
    await auth.set_password(PASSWORD)
    controlled_scrypt.release.clear()
    controlled_scrypt.reset()

    checks = [asyncio.create_task(auth.check_password(PASSWORD)) for _ in range(BURST)]
    await wait_until(lambda: controlled_scrypt.calls >= 1)
    await asyncio.sleep(10 * POLL_STEP_S)  # give every extra check the chance to start hashing
    assert controlled_scrypt.calls <= MAX_SIMULTANEOUS_HASHES
    assert controlled_scrypt.active <= MAX_SIMULTANEOUS_HASHES

    checks[-1].cancel()  # BURST exceeds the bound, so this one is still queued
    controlled_scrypt.release.set()
    results = await asyncio.gather(*checks, return_exceptions=True)

    assert results[:-1] == [True] * (BURST - 1)
    assert isinstance(results[-1], asyncio.CancelledError)
    assert controlled_scrypt.max_active <= MAX_SIMULTANEOUS_HASHES
    assert controlled_scrypt.calls == BURST - 1  # the cancelled waiter never hashed
    assert controlled_scrypt.stalled is False
