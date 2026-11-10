"""Issue #30: a database from a newer version must be refused before anything is written."""

from __future__ import annotations

import contextlib
import hashlib
import sqlite3
from pathlib import Path

import pytest

from bsmm.config import RuntimeConfig
from bsmm.storage.db import MIGRATIONS, Database
from bsmm.storage.store import Store

LATEST = MIGRATIONS[-1][0]
NEWER = LATEST + 1


def _seed(path: Path, version: int) -> None:
    """A database as an installed app would have left it: default journal mode, one recognisable row."""
    with contextlib.closing(sqlite3.connect(path)) as conn:
        conn.execute("CREATE TABLE kv (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("INSERT INTO kv (key, value) VALUES ('keep.me', '\"precious\"')")
        conn.execute(f"PRAGMA user_version = {version}")
        conn.commit()


def _snapshot(folder: Path) -> dict[str, str]:
    """File name -> content hash, so added sidecar files and changed bytes both show up."""
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.iterdir())}


async def test_newer_database_is_refused_and_left_untouched(tmp_path: Path) -> None:
    path = tmp_path / "bsmm.db"
    _seed(path, NEWER)
    before = _snapshot(tmp_path)

    db = Database(path)
    try:
        with pytest.raises(RuntimeError) as exc:
            await db.connect()
    finally:
        await db.close()  # only matters when the guard is missing and the connection stayed open

    message = str(exc.value).lower()
    assert "newer" in message and "reinstall" in message and "backup" in message
    assert str(NEWER) in message
    assert _snapshot(tmp_path) == before  # no journal-mode change, no sidecars, no schema or record changes

    with contextlib.closing(sqlite3.connect(path)) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == NEWER
        assert conn.execute("SELECT value FROM kv WHERE key = 'keep.me'").fetchone()[0] == '"precious"'
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        assert tables == {"kv"}


async def test_newer_database_stops_startup_before_the_secret_key_is_created(tmp_path: Path) -> None:
    _seed(tmp_path / "bsmm.db", NEWER)
    before = _snapshot(tmp_path)

    with pytest.raises(RuntimeError, match="newer"):
        store = await Store.open(RuntimeConfig(data_dir=tmp_path, offline=True, no_update_check=True))
        await store.close()  # reached only when the guard is missing

    assert _snapshot(tmp_path) == before
    assert not (tmp_path / "secret.key").exists()


async def test_current_version_database_still_opens(tmp_path: Path) -> None:
    db = Database(tmp_path / "bsmm.db")
    await db.connect()
    await db.close()
    db = Database(tmp_path / "bsmm.db")
    await db.connect()
    try:
        assert await db.schema_version() == LATEST
    finally:
        await db.close()


async def test_older_supported_database_still_migrates(tmp_path: Path) -> None:
    path = tmp_path / "bsmm.db"
    with contextlib.closing(sqlite3.connect(path)) as conn:
        conn.executescript(MIGRATIONS[0][1])
        conn.execute("PRAGMA user_version = 1")
        conn.execute("INSERT INTO kv (key, value) VALUES ('keep.me', '\"precious\"')")
        conn.commit()

    db = Database(path)
    await db.connect()
    try:
        assert await db.schema_version() == LATEST
        assert await db.scalar("SELECT value FROM kv WHERE key = 'keep.me'") == '"precious"'
    finally:
        await db.close()
