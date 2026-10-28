"""Transaction ownership regressions; deterministic barriers, no external I/O."""
import asyncio
from contextlib import suppress

import pytest

from bsmm.models import DeviceInfo, Event
from bsmm.storage.store import Store


@pytest.fixture
async def store():
    value = await Store.open_memory()
    yield value
    await value.close()


@pytest.mark.parametrize("writer", ["kv", "many", "event", "device"])
async def test_mixed_writer_cannot_commit_failed_transaction(store, writer):
    entered, release, attempted = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def transaction():
        with pytest.raises(RuntimeError, match="rollback"):
            async with store.db.tx() as conn:
                await conn.execute("INSERT INTO kv VALUES ('rollback', '1')")
                entered.set()
                await release.wait()
                raise RuntimeError("rollback")

    async def other():
        await entered.wait()
        attempted.set()
        if writer == "kv":
            await store.kv_set("other", 2)
        elif writer == "many":
            await store.db.executemany("INSERT INTO kv VALUES (?, ?)", [("other", "2")])
        elif writer == "event":
            await store.add_event(Event(type="test", title="independent"))
        else:
            await store.add_device(DeviceInfo(driver="sim", family="sim", model="test", host="test", port=80))

    first = asyncio.create_task(transaction())
    second = asyncio.create_task(other())
    await attempted.wait()
    # Queue a SQLite barrier behind the competing writer's first statement. This does
    # not acquire the application lock and does not itself commit anything.
    await store.db.conn.execute("SELECT 1")
    await store.db.conn.execute("SELECT 1")
    release.set()
    await asyncio.wait_for(asyncio.gather(first, second), 2)
    assert await store.kv_get("rollback") is None
    if writer in ("kv", "many"):
        assert await store.kv_get("other") == 2
    elif writer == "event":
        assert len(await store.list_events()) == 1
    else:
        assert len(await store.list_devices()) == 1


async def test_nested_helpers_rollback_without_deadlock(store):
    async def failing():
        async with store.db.tx():
            await store.kv_set("nested", 1)
            await store.add_event(Event(type="test", title="rollback"))
            await store.kv_add_float("counter", 1)
            raise RuntimeError("rollback")

    with pytest.raises(RuntimeError, match="rollback"):
        await asyncio.wait_for(failing(), 2)
    assert await store.kv_get("nested") is None
    assert await store.kv_get("counter") is None
    assert await store.list_events() == []


async def test_cancelled_waiter_cannot_rollback_owner(store):
    async with store.db.tx() as conn:
        await conn.execute("INSERT INTO kv VALUES ('owner', '1')")
        waiter = asyncio.create_task(store.kv_set("cancelled", 2))
        await asyncio.sleep(0)
        waiter.cancel()
        with suppress(asyncio.CancelledError):
            await waiter
    assert await store.kv_get("owner") == 1
    assert await store.kv_get("cancelled") is None
    await store.kv_set("next", 3)
    assert await store.kv_get("next") == 3


async def test_cancelled_owner_rolls_back_before_next_writer(store):
    entered = asyncio.Event()

    async def owner():
        async with store.db.tx() as conn:
            await conn.execute("INSERT INTO kv VALUES ('cancelled', '1')")
            entered.set()
            await asyncio.Event().wait()

    task = asyncio.create_task(owner())
    await entered.wait()
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
    await store.kv_set("survivor", 2)
    assert await store.kv_get("cancelled") is None
    assert await store.kv_get("survivor") == 2


@pytest.mark.parametrize("boundary", ["commit", "rollback"])
async def test_repeated_cancellation_retains_sqlite_ownership(store, monkeypatch, boundary):
    entered, release = asyncio.Event(), asyncio.Event()
    original = getattr(store.db.conn, boundary)

    async def held():
        entered.set()
        await release.wait()
        await original()

    monkeypatch.setattr(store.db.conn, boundary, held)

    async def owner():
        async with store.db.tx():
            await store.kv_set("owner", 1)
            if boundary == "rollback":
                raise RuntimeError("rollback")

    first = asyncio.create_task(owner())
    await entered.wait()
    first.cancel()
    await asyncio.sleep(0)
    first.cancel()
    second = asyncio.create_task(store.kv_set("other", 2))
    await asyncio.sleep(0)
    assert not second.done()
    release.set()
    with pytest.raises((asyncio.CancelledError, RuntimeError)):
        await first
    await asyncio.wait_for(second, 2)
    assert await store.kv_get("owner") == (1 if boundary == "commit" else None)
    assert await store.kv_get("other") == 2


async def test_failed_ordinary_write_does_not_leave_pending_transaction(store):
    await store.kv_set("existing", 1)
    import sqlite3

    with pytest.raises(sqlite3.IntegrityError):
        await store.db.executemany("INSERT INTO kv VALUES (?, ?)", [("partial", "2"), ("existing", "3")])
    await store.kv_set("survivor", 4)
    assert await store.kv_get("partial") is None
    assert await store.kv_get("existing") == 1
    assert await store.kv_get("survivor") == 4


async def test_read_cannot_observe_rolled_back_data(store):
    entered, release = asyncio.Event(), asyncio.Event()

    async def owner():
        with pytest.raises(RuntimeError):
            async with store.db.tx():
                await store.kv_set("private", 1)
                entered.set()
                await release.wait()
                raise RuntimeError("rollback")

    task = asyncio.create_task(owner())
    await entered.wait()
    reader = asyncio.create_task(store.kv_get("private"))
    await asyncio.sleep(0)
    release.set()
    await task
    assert await reader is None
