"""The data-access facade the rest of the app uses. All SQL for entities lives here."""

from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any

from bsmm.config import RuntimeConfig
from bsmm.models import AlertRule, Channel, Device, DeviceInfo, Event, Severity, Source
from bsmm.storage.db import Database
from bsmm.storage.samples import SampleStore
from bsmm.storage.secrets import SecretBox


def _j(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), default=str)


def _l(text: str | None, default: Any) -> Any:
    if not text:
        return default
    try:
        return json.loads(text)
    except ValueError:
        return default


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(4)}"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class Store:
    def __init__(self, db: Database, box: SecretBox) -> None:
        self.db = db
        self.box = box
        self.samples = SampleStore(db)

    @classmethod
    async def open(cls, config: RuntimeConfig) -> Store:
        config.ensure_dirs()
        db = Database(config.db_path)
        await db.connect()
        return cls(db, SecretBox.load_or_create(config.key_path))

    @classmethod
    async def open_memory(cls) -> Store:
        db = Database(":memory:")
        await db.connect()
        from cryptography.fernet import Fernet

        return cls(db, SecretBox(Fernet.generate_key()))

    async def close(self) -> None:
        await self.db.close()

    # -- key/value (settings, counters) ----------------------------------------------------------

    async def kv_get(self, key: str, default: Any = None) -> Any:
        row = await self.db.fetchone("SELECT value FROM kv WHERE key = ?", (key,))
        return _l(row["value"], default) if row else default

    async def kv_set(self, key: str, value: Any) -> None:
        await self.db.execute(
            "INSERT INTO kv (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, _j(value)),
        )

    async def kv_delete(self, key: str) -> None:
        await self.db.execute("DELETE FROM kv WHERE key = ?", (key,))

    async def kv_add_float(self, key: str, delta: float) -> float:
        async with self.db.tx() as conn:
            cur = await conn.execute("SELECT value FROM kv WHERE key = ?", (key,))
            row = await cur.fetchone()
            current = float(_l(row["value"], 0.0)) if row else 0.0
            new = current + delta
            await conn.execute(
                "INSERT INTO kv (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, _j(new)),
            )
        return new

    # -- devices ----------------------------------------------------------------------------------

    @staticmethod
    def _device(row: sqlite3.Row) -> Device:
        return Device(
            id=row["id"],
            name=row["name"],
            driver=row["driver"],
            family=row["family"],
            model=row["model"],
            host=row["host"],
            port=row["port"],
            mac=row["mac"],
            hostname=row["hostname"],
            serial=row["serial"],
            firmware=row["firmware"],
            asic_model=row["asic_model"],
            asic_count=row["asic_count"],
            board_version=row["board_version"],
            capabilities=_l(row["capabilities"], []),
            tags=_l(row["tags"], []),
            group=row["grp"],
            notes=row["notes"],
            enabled=bool(row["enabled"]),
            allow_control=bool(row["allow_control"]),
            poll_interval_s=row["poll_interval_s"],
            model_override=row["model_override"],
            created_at=row["created_at"],
            last_seen_at=row["last_seen_at"],
            alt_hosts=_l(row["alt_hosts"], []),
            extra=_l(row["extra"], {}),
        )

    async def list_devices(self) -> list[Device]:
        rows = await self.db.fetchall("SELECT * FROM devices ORDER BY created_at, name")
        return [self._device(r) for r in rows]

    async def get_device(self, device_id: str) -> Device | None:
        row = await self.db.fetchone("SELECT * FROM devices WHERE id = ?", (device_id,))
        return self._device(row) if row else None

    async def find_device(self, info: DeviceInfo) -> Device | None:
        """Find the already-monitored device that this probe result describes (same box, maybe new IP)."""
        if info.mac:
            row = await self.db.fetchone("SELECT * FROM devices WHERE mac = ?", (info.mac.upper(),))
            if row:
                return self._device(row)
        if info.serial:
            row = await self.db.fetchone("SELECT * FROM devices WHERE serial = ?", (info.serial,))
            if row:
                return self._device(row)
        row = await self.db.fetchone("SELECT * FROM devices WHERE host = ? AND port = ?", (info.host, info.port))
        if row:
            return self._device(row)
        for dev in await self.list_devices():
            if info.host in dev.alt_hosts:
                return dev
        return None

    async def add_device(
        self,
        info: DeviceInfo,
        *,
        name: str | None = None,
        tags: list[str] | None = None,
        group: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> Device:
        dev = Device(
            id=new_id("dev"),
            name=name or _default_name(info),
            driver=info.driver,
            family=info.family,
            model=info.model,
            host=info.host,
            port=info.port,
            mac=info.mac.upper() if info.mac else None,
            hostname=info.hostname,
            serial=info.serial,
            firmware=info.firmware,
            asic_model=info.asic_model,
            asic_count=info.asic_count,
            board_version=info.board_version,
            capabilities=list(info.capabilities),
            tags=tags or [],
            group=group,
            extra={**info.extra, **(extra or {})},
        )
        await self.save_device(dev, create=True)
        return dev

    async def save_device(self, dev: Device, *, create: bool = False) -> None:
        values = {
            "id": dev.id,
            "name": dev.name,
            "driver": dev.driver,
            "family": dev.family,
            "model": dev.model,
            "host": dev.host,
            "port": dev.port,
            "mac": dev.mac.upper() if dev.mac else None,
            "hostname": dev.hostname,
            "serial": dev.serial,
            "firmware": dev.firmware,
            "asic_model": dev.asic_model,
            "asic_count": dev.asic_count,
            "board_version": dev.board_version,
            "capabilities": _j([str(c) for c in dev.capabilities]),
            "tags": _j(dev.tags),
            "grp": dev.group,
            "notes": dev.notes,
            "enabled": int(dev.enabled),
            "allow_control": int(dev.allow_control),
            "poll_interval_s": dev.poll_interval_s,
            "model_override": dev.model_override,
            "created_at": dev.created_at,
            "last_seen_at": dev.last_seen_at,
            "alt_hosts": _j(dev.alt_hosts),
            "extra": _j(dev.extra),
        }
        cols = list(values)
        if create:
            sql = f"INSERT INTO devices ({', '.join(cols)}) VALUES ({', '.join(':' + c for c in cols)})"
        else:
            sets = ", ".join(f"{c} = :{c}" for c in cols if c != "id")
            sql = f"UPDATE devices SET {sets} WHERE id = :id"
        await self.db.execute(sql, values)

    async def delete_device(self, device_id: str, *, keep_history: bool = False) -> bool:
        n = await self.db.execute("DELETE FROM devices WHERE id = ?", (device_id,))
        if n and not keep_history:
            await self.samples.delete_device_samples(device_id)
            await self.db.execute("DELETE FROM best_shares WHERE device_id = ?", (device_id,))
        return bool(n)

    async def touch_device(self, device_id: str, ts: float | None = None) -> None:
        await self.db.execute("UPDATE devices SET last_seen_at = ? WHERE id = ?", (ts or time.time(), device_id))

    # -- events ------------------------------------------------------------------------------------

    @staticmethod
    def _event(row: sqlite3.Row) -> Event:
        return Event(
            id=row["id"],
            ts=row["ts"],
            type=row["type"],
            severity=Severity(row["severity"]),
            device_id=row["device_id"],
            title=row["title"],
            body=row["body"],
            data=_l(row["data"], {}),
            dedupe_key=row["dedupe_key"],
            ack_ts=row["ack_ts"],
        )

    async def add_event(self, event: Event) -> Event:
        cur = await self.db.conn.execute(
            "INSERT INTO events (ts, type, severity, device_id, title, body, data, dedupe_key) VALUES (?,?,?,?,?,?,?,?)",
            (event.ts, event.type, event.severity.value, event.device_id, event.title, event.body, _j(event.data), event.dedupe_key),
        )
        await self.db.conn.commit()
        event.id = cur.lastrowid
        return event

    async def list_events(
        self,
        *,
        limit: int = 100,
        before_id: int | None = None,
        since: float | None = None,
        types: list[str] | None = None,
        device_id: str | None = None,
        min_severity: Severity | None = None,
        unacked_only: bool = False,
    ) -> list[Event]:
        where: list[str] = ["1=1"]
        params: list[Any] = []
        if before_id:
            where.append("id < ?")
            params.append(before_id)
        if since:
            where.append("ts >= ?")
            params.append(since)
        if types:
            where.append(f"type IN ({', '.join('?' for _ in types)})")
            params.extend(types)
        if device_id:
            where.append("device_id = ?")
            params.append(device_id)
        if min_severity:
            ok = [s.value for s in Severity if s.rank >= min_severity.rank]
            where.append(f"severity IN ({', '.join('?' for _ in ok)})")
            params.extend(ok)
        if unacked_only:
            where.append("ack_ts IS NULL")
        rows = await self.db.fetchall(
            f"SELECT * FROM events WHERE {' AND '.join(where)} ORDER BY id DESC LIMIT ?", (*params, max(1, min(limit, 1000)))
        )
        return [self._event(r) for r in rows]

    async def events_after(self, event_id: int, *, limit: int = 128) -> list[Event]:
        """Forward-only bounded replay for the alert consumer (not UI pagination)."""
        rows = await self.db.fetchall("SELECT * FROM events WHERE id > ? ORDER BY id LIMIT ?",
                                     (event_id, max(1, min(limit, 1000))))
        return [self._event(r) for r in rows]

    async def ack_event(self, event_id: int) -> bool:
        return bool(await self.db.execute("UPDATE events SET ack_ts = ? WHERE id = ? AND ack_ts IS NULL", (time.time(), event_id)))

    async def ack_all_events(self) -> int:
        return await self.db.execute("UPDATE events SET ack_ts = ? WHERE ack_ts IS NULL", (time.time(),))

    async def prune_events(self, keep_days: float = 180) -> int:
        return await self.db.execute("DELETE FROM events WHERE ts < ?", (time.time() - keep_days * 86400,))

    # -- alert rules / state -----------------------------------------------------------------------

    @staticmethod
    def _rule(row: sqlite3.Row) -> AlertRule:
        return AlertRule(
            id=row["id"],
            name=row["name"],
            kind=row["kind"],
            enabled=bool(row["enabled"]),
            severity=Severity(row["severity"]),
            scope=_l(row["scope"], {"all": True}),
            params=_l(row["params"], {}),
            channel_ids=_l(row["channel_ids"], []),
            cooldown_s=row["cooldown_s"],
            builtin=bool(row["builtin"]),
            created_at=row["created_at"],
        )

    async def list_rules(self) -> list[AlertRule]:
        rows = await self.db.fetchall("SELECT * FROM rules ORDER BY builtin DESC, created_at, name")
        return [self._rule(r) for r in rows]

    async def get_rule(self, rule_id: str) -> AlertRule | None:
        row = await self.db.fetchone("SELECT * FROM rules WHERE id = ?", (rule_id,))
        return self._rule(row) if row else None

    async def save_rule(self, rule: AlertRule) -> None:
        await self.db.execute(
            "INSERT INTO rules (id, name, kind, enabled, severity, scope, params, channel_ids, cooldown_s, builtin, created_at) "
            "VALUES (:id,:name,:kind,:enabled,:severity,:scope,:params,:channel_ids,:cooldown_s,:builtin,:created_at) "
            "ON CONFLICT(id) DO UPDATE SET name=excluded.name, kind=excluded.kind, enabled=excluded.enabled, "
            "severity=excluded.severity, scope=excluded.scope, params=excluded.params, channel_ids=excluded.channel_ids, "
            "cooldown_s=excluded.cooldown_s",
            {
                "id": rule.id,
                "name": rule.name,
                "kind": rule.kind,
                "enabled": int(rule.enabled),
                "severity": rule.severity.value,
                "scope": _j(rule.scope),
                "params": _j(rule.params),
                "channel_ids": _j(rule.channel_ids),
                "cooldown_s": rule.cooldown_s,
                "builtin": int(rule.builtin),
                "created_at": rule.created_at,
            },
        )

    async def delete_rule(self, rule_id: str) -> bool:
        await self.db.execute("DELETE FROM alert_state WHERE rule_id = ?", (rule_id,))
        return bool(await self.db.execute("DELETE FROM rules WHERE id = ?", (rule_id,)))

    async def load_alert_state(self) -> dict[str, dict[str, Any]]:
        rows = await self.db.fetchall("SELECT * FROM alert_state")
        return {
            r["key"]: {"rule_id": r["rule_id"], "device_id": r["device_id"], "since": r["since"], "last_notified": r["last_notified"], "data": _l(r["data"], {})}
            for r in rows
        }

    async def save_alert_state(self, key: str, rule_id: str, device_id: str | None, since: float, last_notified: float | None, data: dict[str, Any]) -> None:
        await self.db.execute(
            "INSERT INTO alert_state (key, rule_id, device_id, since, last_notified, data) VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET last_notified=excluded.last_notified, data=excluded.data",
            (key, rule_id, device_id, since, last_notified, _j(data)),
        )

    async def clear_alert_state(self, key: str) -> None:
        await self.db.execute("DELETE FROM alert_state WHERE key = ?", (key,))

    # -- notification channels ----------------------------------------------------------------------

    def _channel(self, row: sqlite3.Row) -> Channel:
        return Channel(
            id=row["id"],
            kind=row["kind"],
            name=row["name"],
            enabled=bool(row["enabled"]),
            config=_l(row["config"], {}),
            has_secret=bool(row["secret_enc"]),
            min_severity=Severity(row["min_severity"]),
            created_at=row["created_at"],
        )

    async def list_channels(self) -> list[Channel]:
        return [self._channel(r) for r in await self.db.fetchall("SELECT * FROM channels ORDER BY created_at")]

    async def get_channel(self, channel_id: str) -> Channel | None:
        row = await self.db.fetchone("SELECT * FROM channels WHERE id = ?", (channel_id,))
        return self._channel(row) if row else None

    async def channel_secret(self, channel_id: str) -> dict[str, str]:
        row = await self.db.fetchone("SELECT secret_enc FROM channels WHERE id = ?", (channel_id,))
        secret: dict[str, str] = _l(self.box.decrypt(row["secret_enc"]) if row else None, {})
        return secret

    async def save_channel(self, ch: Channel, secret: dict[str, str] | None = None) -> None:
        """``secret=None`` keeps the stored secret; ``{}`` clears it."""
        existing = await self.db.fetchone("SELECT secret_enc FROM channels WHERE id = ?", (ch.id,))
        if secret is None:
            enc = existing["secret_enc"] if existing else None
        else:
            enc = self.box.encrypt(_j(secret)) if secret else None
        await self.db.execute(
            "INSERT INTO channels (id, kind, name, enabled, config, secret_enc, min_severity, created_at) "
            "VALUES (:id,:kind,:name,:enabled,:config,:secret,:min_severity,:created_at) "
            "ON CONFLICT(id) DO UPDATE SET kind=excluded.kind, name=excluded.name, enabled=excluded.enabled, "
            "config=excluded.config, secret_enc=excluded.secret_enc, min_severity=excluded.min_severity",
            {
                "id": ch.id,
                "kind": ch.kind,
                "name": ch.name,
                "enabled": int(ch.enabled),
                "config": _j(ch.config),
                "secret": enc,
                "min_severity": ch.min_severity.value,
                "created_at": ch.created_at,
            },
        )

    async def delete_channel(self, channel_id: str) -> bool:
        return bool(await self.db.execute("DELETE FROM channels WHERE id = ?", (channel_id,)))

    # -- data sources ----------------------------------------------------------------------------------

    def _source(self, row: sqlite3.Row) -> Source:
        return Source(
            id=row["id"],
            kind=row["kind"],
            name=row["name"],
            url=row["url"],
            enabled=bool(row["enabled"]),
            options=_l(row["options"], {}),
            has_secret=bool(row["secret_enc"]),
            created_at=row["created_at"],
        )

    async def list_sources(self) -> list[Source]:
        return [self._source(r) for r in await self.db.fetchall("SELECT * FROM sources ORDER BY created_at")]

    async def get_source(self, source_id: str) -> Source | None:
        row = await self.db.fetchone("SELECT * FROM sources WHERE id = ?", (source_id,))
        return self._source(row) if row else None

    async def source_secret(self, source_id: str) -> dict[str, str]:
        row = await self.db.fetchone("SELECT secret_enc FROM sources WHERE id = ?", (source_id,))
        secret: dict[str, str] = _l(self.box.decrypt(row["secret_enc"]) if row else None, {})
        return secret

    async def save_source(self, src: Source, secret: dict[str, str] | None = None) -> None:
        existing = await self.db.fetchone("SELECT secret_enc FROM sources WHERE id = ?", (src.id,))
        if secret is None:
            enc = existing["secret_enc"] if existing else None
        else:
            enc = self.box.encrypt(_j(secret)) if secret else None
        await self.db.execute(
            "INSERT INTO sources (id, kind, name, url, enabled, options, secret_enc, created_at) "
            "VALUES (:id,:kind,:name,:url,:enabled,:options,:secret,:created_at) "
            "ON CONFLICT(id) DO UPDATE SET kind=excluded.kind, name=excluded.name, url=excluded.url, "
            "enabled=excluded.enabled, options=excluded.options, secret_enc=excluded.secret_enc",
            {
                "id": src.id,
                "kind": src.kind,
                "name": src.name,
                "url": src.url,
                "enabled": int(src.enabled),
                "options": _j(src.options),
                "secret": enc,
                "created_at": src.created_at,
            },
        )

    async def delete_source(self, source_id: str) -> bool:
        return bool(await self.db.execute("DELETE FROM sources WHERE id = ?", (source_id,)))

    # -- API tokens / sessions -----------------------------------------------------------------------------

    async def create_token(self, name: str, scope: str, expires_at: float | None = None) -> tuple[str, str]:
        """Returns (token_id, plaintext_token). The plaintext is shown once and never stored."""
        token = "bsmm_" + secrets.token_urlsafe(32)
        token_id = new_id("tok")
        await self.db.execute(
            "INSERT INTO tokens (id, name, hash, scope, created_at, expires_at) VALUES (?,?,?,?,?,?)",
            (token_id, name, hash_token(token), scope, time.time(), expires_at),
        )
        return token_id, token

    async def verify_token(self, token: str) -> dict[str, Any] | None:
        row = await self.db.fetchone("SELECT * FROM tokens WHERE hash = ?", (hash_token(token),))
        if not row:
            return None
        if row["expires_at"] and row["expires_at"] < time.time():
            return None
        await self.db.execute("UPDATE tokens SET last_used_at = ? WHERE id = ?", (time.time(), row["id"]))
        return {"id": row["id"], "name": row["name"], "scope": row["scope"]}

    async def list_tokens(self) -> list[dict[str, Any]]:
        rows = await self.db.fetchall("SELECT id, name, scope, created_at, last_used_at, expires_at FROM tokens ORDER BY created_at")
        return [dict(r) for r in rows]

    async def delete_token(self, token_id: str) -> bool:
        return bool(await self.db.execute("DELETE FROM tokens WHERE id = ?", (token_id,)))

    async def create_session(self, ttl_s: float, user_agent: str | None, ip: str | None) -> str:
        sid = secrets.token_urlsafe(32)
        now = time.time()
        await self.db.execute(
            "INSERT INTO sessions (id_hash, created_at, expires_at, last_seen_at, user_agent, ip) VALUES (?,?,?,?,?,?)",
            (hash_token(sid), now, now + ttl_s, now, (user_agent or "")[:200], ip),
        )
        return sid

    async def verify_session(self, sid: str) -> bool:
        row = await self.db.fetchone("SELECT expires_at FROM sessions WHERE id_hash = ?", (hash_token(sid),))
        return not (not row or row["expires_at"] < time.time())

    async def delete_session(self, sid: str) -> None:
        await self.db.execute("DELETE FROM sessions WHERE id_hash = ?", (hash_token(sid),))

    async def purge_sessions(self) -> None:
        await self.db.execute("DELETE FROM sessions WHERE expires_at < ?", (time.time(),))

    async def delete_all_sessions(self) -> None:
        await self.db.execute("DELETE FROM sessions")

    # -- blocks / best shares / audit / network ------------------------------------------------------------------

    async def add_block_found(self, *, hash_: str, height: int, ts: float, device_id: str | None, address: str | None,
                              reward_sats: int | None, source: str, data: dict[str, Any] | None = None) -> bool:
        """True if this block was new (the same block can be reported by several signals)."""
        n = await self.db.execute(
            "INSERT OR IGNORE INTO blocks_found (hash, height, ts, device_id, address, reward_sats, source, data) VALUES (?,?,?,?,?,?,?,?)",
            (hash_, height, ts, device_id, address, reward_sats, source, _j(data or {})),
        )
        return n > 0

    async def list_blocks_found(self) -> list[dict[str, Any]]:
        rows = await self.db.fetchall("SELECT * FROM blocks_found ORDER BY height DESC")
        return [{**dict(r), "data": _l(r["data"], {})} for r in rows]

    async def add_best_share(self, device_id: str, difficulty: float, ts: float | None = None) -> None:
        await self.db.execute("INSERT INTO best_shares (device_id, ts, difficulty) VALUES (?,?,?)", (device_id, ts or time.time(), difficulty))

    async def best_shares_leaderboard(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = await self.db.fetchall(
            "SELECT device_id, MAX(difficulty) AS difficulty, MAX(ts) AS ts FROM best_shares GROUP BY device_id ORDER BY difficulty DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in rows]

    async def add_audit(self, actor: str, action: str, device_id: str | None, params: dict[str, Any], result: dict[str, Any]) -> None:
        # never persist secrets that were part of a change request
        safe = {k: ("***" if any(s in k.lower() for s in ("pass", "secret", "token", "key")) else v) for k, v in params.items()}
        await self.db.execute(
            "INSERT INTO audit (ts, actor, action, device_id, params, result) VALUES (?,?,?,?,?,?)",
            (time.time(), actor, action, device_id, _j(safe), _j(result)),
        )

    async def list_audit(self, limit: int = 100, device_id: str | None = None) -> list[dict[str, Any]]:
        if device_id:
            rows = await self.db.fetchall("SELECT * FROM audit WHERE device_id = ? ORDER BY id DESC LIMIT ?", (device_id, limit))
        else:
            rows = await self.db.fetchall("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,))
        return [{**dict(r), "params": _l(r["params"], {}), "result": _l(r["result"], {})} for r in rows]

    async def add_network_snapshot(self, ts: int, height: int | None, difficulty: float | None, hashrate: float | None,
                                   price: float | None, source: str) -> None:
        await self.db.execute(
            "INSERT OR REPLACE INTO network_snapshots (ts, height, difficulty, network_hashrate_hs, btc_price_usd, source) VALUES (?,?,?,?,?,?)",
            (ts, height, difficulty, hashrate, price, source),
        )

    # -- backup ---------------------------------------------------------------------------------------------------

    async def backup_to(self, target: Path) -> None:
        """Consistent copy of the whole database (uses SQLite's online backup)."""
        import sqlite3 as _sqlite

        def prepare() -> None:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.unlink(missing_ok=True)

        await asyncio.to_thread(prepare)
        dest = _sqlite.connect(str(target))
        try:
            await self.db.conn.backup(dest)
        finally:
            dest.close()


def _default_name(info: DeviceInfo) -> str:
    if info.hostname and info.hostname.lower() not in {"bitaxe", "esp-miner", "nerdqaxe", "axeos"}:
        return info.hostname
    return f"{info.model} ({info.host})"
