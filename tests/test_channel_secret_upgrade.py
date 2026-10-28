"""SEC-03: reopen fake v1.1.1 channel rows without exposing or losing credentials."""
import json

import httpx
import pytest

from bsmm.api.app import create_app
from bsmm.config import RuntimeConfig
from bsmm.context import AppContext
from bsmm.notify.channels import CHANNEL_CLASSES
from bsmm.storage.db import Database
from bsmm.storage.secrets import SecretBox
from bsmm.storage.store import Store


@pytest.fixture
def config(tmp_path, monkeypatch):
    monkeypatch.delenv("BSMM_SECRET_KEY", raising=False)
    cfg = RuntimeConfig(data_dir=tmp_path, offline=True, no_update_check=True,
                        auth_mode=None, admin_password=None)
    cfg.ensure_dirs()
    return cfg


def fields(kind):
    public = {f.name: f.default if f.default is not None else "fixture-public"
              for f in CHANNEL_CLASSES[kind].fields if not f.secret}
    public["extension"] = {"preserve": [True, 17, " unchanged "]}
    private = {f.name: f" \tFAKE-ONLY-{kind}-{f.name}-雪\n "
               for f in CHANNEL_CLASSES[kind].fields if f.secret}
    return public, private


async def seed_legacy(config, kind, mode="plaintext"):
    """Raw INSERT matches v1.1.1 import/save_channel, bypassing repaired writes.

    The released importer kept config verbatim, disabled the row and passed
    secret={}; an operator could subsequently enable it. No actual sends.
    """
    public, private = fields(kind)
    encrypted = {}
    legacy = dict(private)
    if mode == "conflict":
        encrypted = {name: f" \tFAKE-ENCRYPTED-{name}\n " for name in private}
    elif mode == "partial":
        encrypted = {next(iter(private)): " \tFAKE-ENCRYPTED-FIRST\n ", "extension_secret": " fake-extra "}
    elif mode == "empty-encrypted":
        encrypted = dict.fromkeys(private, "")
    elif mode == "encrypted-only":
        encrypted, legacy = private, {}
    box = SecretBox.load_or_create(config.key_path)
    enc = box.encrypt(json.dumps(encrypted)) if encrypted else None
    db = Database(config.db_path)
    await db.connect()
    try:
        for enabled in (False, True):
            await db.execute(
                "INSERT INTO channels (id, kind, name, enabled, config, secret_enc, min_severity, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (f"legacy-{int(enabled)}", kind, " unchanged name ", int(enabled),
                 json.dumps(public | legacy), enc, "warning", 1234.5),
            )
        await db.execute("INSERT INTO kv (key, value) VALUES (?, ?)", ("upgrade-neighbor", '["unchanged"]'))
        before = [dict(row) for row in await db.fetchall("SELECT * FROM channels ORDER BY id")]
        assert all(json.loads(row["config"]) == public | legacy for row in before)
        assert all(row["secret_enc"] == enc for row in before)
        return before, public, private, encrypted
    finally:
        await db.close()


@pytest.mark.parametrize("kind", list(CHANNEL_CLASSES))
@pytest.mark.parametrize("surface", ["read-list", "admin-export", "plaintext-column"])
async def test_sec03_legacy_reopen_excludes_canonical_secrets(config, kind, surface):
    _, public, private, _ = await seed_legacy(config, kind)
    # Reopen the persisted old-format database through the real app creation path.
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: pytest.fail("unexpected send"))) as http:
        ctx = await AppContext.create(config, http=http)
        try:
            await ctx.settings.update({"auth": {"mode": "password"}})
            _, reader = await ctx.store.create_token("fixture-reader", "read")
            _, admin = await ctx.store.create_token("fixture-admin", "admin")
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(ctx=ctx)),
                                        base_url="http://127.0.0.1", trust_env=False) as client:
                if surface == "plaintext-column":
                    rows = await ctx.store.db.fetchall("SELECT config FROM channels")
                    configs = [json.loads(row["config"]) for row in rows]
                else:
                    path = "/api/v1/notifications/channels" if surface == "read-list" else "/api/v1/system/export"
                    token = reader if surface == "read-list" else admin
                    response = await client.get(path, headers={"Authorization": f"Bearer {token}"})
                    assert response.status_code == 200
                    # Test the entire public response, not merely the config projection.
                    assert all(value.strip() not in response.text for value in private.values()), "legacy credential exposed"
                    configs = [row["config"] for row in response.json()["channels"]]
                assert all(not set(private).intersection(cfg) for cfg in configs), "canonical secret field exposed"
                assert all(cfg == public for cfg in configs), "non-secret configuration changed"
        finally:
            await ctx.stop()


@pytest.mark.parametrize("kind", list(CHANNEL_CLASSES))
@pytest.mark.parametrize("mode", ["plaintext", "conflict", "partial", "empty-encrypted", "encrypted-only"])
async def test_sec03_upgrade_preserves_credentials_and_is_idempotent(config, kind, mode):
    before, public, private, encrypted = await seed_legacy(config, kind, mode)
    key_before = config.key_path.read_bytes()
    key_stat = config.key_path.stat()
    expected = private | encrypted
    if mode == "empty-encrypted":
        expected = private  # BaseChannel.value previously fell back to config for empty encrypted values.
    normalized = None
    for _ in range(3):
        store = await Store.open(config)
        try:
            rows = [dict(row) for row in await store.db.fetchall("SELECT * FROM channels ORDER BY id")]
            for old, row in zip(before, rows, strict=True):
                assert {k: v for k, v in row.items() if k not in ("config", "secret_enc")} == {
                    k: v for k, v in old.items() if k not in ("config", "secret_enc")}
                assert json.loads(row["config"]) == public, "plaintext config not normalized"
                assert await store.channel_secret(row["id"]) == expected, "exact credentials or precedence changed"
                assert row["secret_enc"].startswith("enc:v1:")
                assert all(value.strip() not in row["secret_enc"] for value in private.values())
                if mode in ("conflict", "encrypted-only"):
                    assert row["secret_enc"] == old["secret_enc"], "unchanged encrypted credentials were rewritten"
                channel = await store.get_channel(row["id"])
                assert channel is not None and channel.has_secret and channel.config == public
            if normalized is not None:
                assert rows == normalized, "reopening rewrote normalized rows"
            normalized = rows
            await store._normalize_channel_secrets()
            assert [dict(row) for row in await store.db.fetchall("SELECT * FROM channels ORDER BY id")] == rows
            assert await store.kv_get("upgrade-neighbor") == ["unchanged"]
            assert await store.db.scalar("PRAGMA integrity_check") == "ok"
            assert await store.db.schema_version() == 1
        finally:
            await store.close()
        assert config.key_path.read_bytes() == key_before
        assert config.key_path.stat().st_mtime_ns == key_stat.st_mtime_ns
        assert config.key_path.stat().st_mode == key_stat.st_mode


@pytest.mark.parametrize("kind", list(CHANNEL_CLASSES))
@pytest.mark.parametrize("value", [None, "", " \t\n "], ids=["null", "empty", "whitespace"])
async def test_sec03_upgrade_empty_fields(config, kind, value):
    _, public, private, _ = await seed_legacy(config, kind)
    db = Database(config.db_path)
    await db.connect()
    try:
        await db.execute("UPDATE channels SET config = ?", (json.dumps(public | dict.fromkeys(private, value)),))
    finally:
        await db.close()
    store = await Store.open(config)
    try:
        for channel in await store.list_channels():
            assert channel.config == public
            expected = {} if value is None else dict.fromkeys(private, value)
            assert await store.channel_secret(channel.id) == expected
        rows = [dict(row) for row in await store.db.fetchall("SELECT * FROM channels ORDER BY id")]
        await store._normalize_channel_secrets()
        assert [dict(row) for row in await store.db.fetchall("SELECT * FROM channels ORDER BY id")] == rows
    finally:
        await store.close()


@pytest.mark.parametrize("failure", ["unreadable", "invalid-json", "invalid-shape", "encrypt", "write"])
async def test_sec03_upgrade_failure_keeps_rows_and_closes_store(config, monkeypatch, failure):
    await seed_legacy(config, "telegram")
    key_before = config.key_path.read_bytes()
    box = SecretBox.load_or_create(config.key_path)
    db = Database(config.db_path)
    await db.connect()
    try:
        damaged = {
            "unreadable": "enc:v1:FAKE-UNREADABLE",
            "invalid-json": box.encrypt("FAKE-NOT-JSON"),
            "invalid-shape": box.encrypt('["FAKE-NOT-A-MAPPING"]'),
        }
        if failure in damaged:
            await db.execute("UPDATE channels SET secret_enc = ? WHERE id = 'legacy-1'", (damaged[failure],))
        if failure == "write":
            await db.execute("CREATE TRIGGER fail_upgrade BEFORE UPDATE ON channels "
                             "WHEN OLD.id = 'legacy-1' BEGIN SELECT RAISE(ABORT, 'fixture write failure'); END")
        before = [dict(row) for row in await db.fetchall("SELECT * FROM channels ORDER BY id")]
    finally:
        await db.close()

    closed = []
    original_close = Database.close
    original_encrypt = SecretBox.encrypt
    calls = 0

    async def close(self):
        await original_close(self)
        closed.append(self._conn is None)

    def encrypt(self, plaintext):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("fixture encryption failure")
        return original_encrypt(self, plaintext)

    with monkeypatch.context() as patch:
        patch.setattr(Database, "close", close)
        if failure == "encrypt":
            patch.setattr(SecretBox, "encrypt", encrypt)
        import sqlite3

        error = RuntimeError if failure == "encrypt" else sqlite3.IntegrityError if failure == "write" else ValueError
        message = "fixture .* failure" if failure in ("encrypt", "write") else "Cannot safely upgrade notification credentials"
        with pytest.raises(error, match=message):
            await Store.open(config)
        assert closed == [True], "failed open left its connection running"

    db = Database(config.db_path)
    await db.connect()
    try:
        after = [dict(row) for row in await db.fetchall("SELECT * FROM channels ORDER BY id")]
        assert after == before, "failed upgrade partially changed persisted rows"
        assert await db.scalar("PRAGMA integrity_check") == "ok"
        # Remove only the injected failure and prove the same persisted data can retry.
        if failure in damaged:
            await db.execute("UPDATE channels SET secret_enc = NULL WHERE id = 'legacy-1'")
        elif failure == "write":
            await db.execute("DROP TRIGGER fail_upgrade")
    finally:
        await db.close()
    store = await Store.open(config)
    try:
        public, private = fields("telegram")
        for channel in await store.list_channels():
            assert channel.config == public
            assert await store.channel_secret(channel.id) == private
    finally:
        await store.close()
    assert config.key_path.read_bytes() == key_before
