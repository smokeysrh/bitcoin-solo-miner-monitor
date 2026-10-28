"""SQLite access: one WAL-mode connection, forward-only migrations tracked in ``PRAGMA user_version``."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import sqlite3
from collections.abc import AsyncIterator, Coroutine, Iterable, Sequence
from pathlib import Path
from typing import Any

import aiosqlite

from bsmm.storage import metrics as mx

log = logging.getLogger(__name__)


def _v1() -> str:
    parts = [
        """
CREATE TABLE devices (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  driver TEXT NOT NULL,
  family TEXT NOT NULL,
  model TEXT NOT NULL,
  host TEXT NOT NULL,
  port INTEGER NOT NULL,
  mac TEXT,
  hostname TEXT,
  serial TEXT,
  firmware TEXT,
  asic_model TEXT,
  asic_count INTEGER,
  board_version TEXT,
  capabilities TEXT NOT NULL DEFAULT '[]',
  tags TEXT NOT NULL DEFAULT '[]',
  grp TEXT,
  notes TEXT,
  enabled INTEGER NOT NULL DEFAULT 1,
  allow_control INTEGER NOT NULL DEFAULT 1,
  poll_interval_s REAL,
  model_override TEXT,
  created_at REAL NOT NULL,
  last_seen_at REAL,
  alt_hosts TEXT NOT NULL DEFAULT '[]',
  extra TEXT NOT NULL DEFAULT '{}'
);
CREATE UNIQUE INDEX devices_endpoint ON devices(host, port);
CREATE INDEX devices_mac ON devices(mac);
CREATE INDEX devices_serial ON devices(serial);
""",
        mx.raw_table_ddl(),
        mx.rollup_table_ddl("samples_1m"),
        mx.rollup_table_ddl("samples_1h"),
        mx.rollup_table_ddl("samples_1d"),
        """
CREATE TABLE kv (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  type TEXT NOT NULL,
  severity TEXT NOT NULL,
  device_id TEXT,
  title TEXT NOT NULL,
  body TEXT,
  data TEXT NOT NULL DEFAULT '{}',
  dedupe_key TEXT,
  ack_ts REAL
);
CREATE INDEX events_ts ON events(ts DESC);
CREATE INDEX events_type ON events(type, ts DESC);
CREATE INDEX events_device ON events(device_id, ts DESC);

CREATE TABLE alert_state (
  key TEXT PRIMARY KEY,
  rule_id TEXT NOT NULL,
  device_id TEXT,
  since REAL NOT NULL,
  last_notified REAL,
  data TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE rules (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  kind TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  severity TEXT NOT NULL DEFAULT 'warning',
  scope TEXT NOT NULL DEFAULT '{}',
  params TEXT NOT NULL DEFAULT '{}',
  channel_ids TEXT NOT NULL DEFAULT '[]',
  cooldown_s REAL NOT NULL DEFAULT 3600,
  builtin INTEGER NOT NULL DEFAULT 0,
  created_at REAL NOT NULL
);

CREATE TABLE channels (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  name TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  config TEXT NOT NULL DEFAULT '{}',
  secret_enc TEXT,
  min_severity TEXT NOT NULL DEFAULT 'info',
  created_at REAL NOT NULL
);

CREATE TABLE sources (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  name TEXT NOT NULL,
  url TEXT,
  enabled INTEGER NOT NULL DEFAULT 1,
  options TEXT NOT NULL DEFAULT '{}',
  secret_enc TEXT,
  created_at REAL NOT NULL
);

CREATE TABLE tokens (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  hash TEXT NOT NULL UNIQUE,
  scope TEXT NOT NULL,
  created_at REAL NOT NULL,
  last_used_at REAL,
  expires_at REAL
);

CREATE TABLE sessions (
  id_hash TEXT PRIMARY KEY,
  created_at REAL NOT NULL,
  expires_at REAL NOT NULL,
  last_seen_at REAL,
  user_agent TEXT,
  ip TEXT
);

CREATE TABLE blocks_found (
  hash TEXT PRIMARY KEY,
  height INTEGER NOT NULL,
  ts REAL NOT NULL,
  device_id TEXT,
  address TEXT,
  reward_sats INTEGER,
  source TEXT NOT NULL,
  data TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE best_shares (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  device_id TEXT NOT NULL,
  ts REAL NOT NULL,
  difficulty REAL NOT NULL
);
CREATE INDEX best_shares_device ON best_shares(device_id, ts DESC);

CREATE TABLE audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  device_id TEXT,
  params TEXT NOT NULL DEFAULT '{}',
  result TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX audit_ts ON audit(ts DESC);

CREATE TABLE network_snapshots (
  ts INTEGER PRIMARY KEY,
  height INTEGER,
  difficulty REAL,
  network_hashrate_hs REAL,
  btc_price_usd REAL,
  source TEXT
);
""",
    ]
    return "\n".join(parts)


def _v2() -> str:
    # Historical valid counts cannot be inferred from n: AVG ignored missing metrics.
    # Preserve retained data and leave unknown weights NULL (queries disclose approximation).
    return "\n".join(f"ALTER TABLE {table} ADD COLUMN {m.name}_n INTEGER;"
                     for table, _, _ in mx.LEVELS for m in mx.METRICS if m.kind != "counter")


#: (version, script). Never edit a released migration; append a new one.
MIGRATIONS: list[tuple[int, str]] = [(1, _v1()), (2, _v2())]


class Database:
    def __init__(self, path: Path | str) -> None:
        self.path = str(path)
        self._conn: aiosqlite.Connection | None = None
        self._tx_lock = asyncio.Lock()
        self._tx_owner: asyncio.Task[Any] | None = None

    async def connect(self) -> None:
        if self._conn is not None:
            return
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA synchronous=NORMAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self._conn.execute("PRAGMA busy_timeout=5000")
        await self._conn.execute("PRAGMA temp_store=MEMORY")
        await self._migrate()

    async def close(self) -> None:
        if self._conn is not None:
            with contextlib.suppress(Exception):
                await self._conn.execute("PRAGMA optimize")
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("database is not connected")
        return self._conn

    async def _migrate(self) -> None:
        async with self.conn.execute("PRAGMA user_version") as cur:
            row = await cur.fetchone()
        current = int(row[0]) if row else 0
        for version, script in MIGRATIONS:
            if version <= current:
                continue
            log.info("Applying database migration %s", version)
            try:
                await self.conn.executescript(f"BEGIN;\n{script}\nPRAGMA user_version = {version};\nCOMMIT;")
            except Exception:
                await self.conn.rollback()
                raise

    async def schema_version(self) -> int:
        async with self.conn.execute("PRAGMA user_version") as cur:
            row = await cur.fetchone()
        return int(row[0]) if row else 0

    # -- helpers --------------------------------------------------------------------------

    async def execute(self, sql: str, params: Sequence[Any] | dict[str, Any] = ()) -> int:
        async with self.tx() as conn, conn.execute(sql, params) as cur:
            rowcount = cur.rowcount
        return rowcount

    async def executemany(self, sql: str, rows: Iterable[Sequence[Any] | dict[str, Any]]) -> None:
        async with self.tx() as conn:
            await conn.executemany(sql, rows)

    async def fetchall(self, sql: str, params: Sequence[Any] | dict[str, Any] = ()) -> list[sqlite3.Row]:
        async with self.read_connection() as conn, conn.execute(sql, params) as cur:
            return list(await cur.fetchall())

    async def fetchone(self, sql: str, params: Sequence[Any] | dict[str, Any] = ()) -> sqlite3.Row | None:
        async with self.read_connection() as conn, conn.execute(sql, params) as cur:
            return await cur.fetchone()

    async def scalar(self, sql: str, params: Sequence[Any] | dict[str, Any] = ()) -> Any:
        row = await self.fetchone(sql, params)
        return row[0] if row else None

    @contextlib.asynccontextmanager
    async def read_connection(self) -> AsyncIterator[aiosqlite.Connection]:
        """Do not expose another task's uncommitted writes (also used by backups)."""
        if self._tx_owner is asyncio.current_task():
            yield self.conn
        else:
            async with self._tx_lock:
                yield self.conn

    @staticmethod
    async def _settle(operation: Coroutine[Any, Any, None]) -> None:
        """SQLite work keeps running after cancellation; retain ownership until it finishes."""
        task = asyncio.create_task(operation)
        cancelled = False
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                cancelled = True
        task.result()
        if cancelled:
            raise asyncio.CancelledError

    @contextlib.asynccontextmanager
    async def tx(self) -> AsyncIterator[aiosqlite.Connection]:
        """One task owns writes through commit/rollback. Nested calls join its transaction.

        Do not hand the yielded connection to another task or commit it directly.
        Only the outermost scope decides commit/rollback.
        """
        if self._tx_owner is asyncio.current_task():
            yield self.conn
            return
        async with self._tx_lock:
            self._tx_owner = asyncio.current_task()
            try:
                try:
                    await self.conn.execute("BEGIN")
                    yield self.conn
                except BaseException:
                    await self._settle(self.conn.rollback())
                    raise
                else:
                    # A cancellation during commit cannot undo an already committed write.
                    try:
                        await self._settle(self.conn.commit())
                    except Exception:
                        await self._settle(self.conn.rollback())
                        raise
            finally:
                self._tx_owner = None
