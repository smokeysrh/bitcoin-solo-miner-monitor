import time

import pytest

from bsmm.models import AlertRule, Channel, DeviceInfo, Event, Severity, Source, Telemetry
from bsmm.storage.samples import Retention, parse_metric_spec, telemetry_to_row
from bsmm.storage.store import Store


@pytest.fixture
async def store():
    s = await Store.open_memory()
    yield s
    await s.close()


def info(host="10.0.0.5", mac="AA:BB:CC:00:00:01", **kw) -> DeviceInfo:
    return DeviceInfo(driver="axeos", family="bitaxe", model="Bitaxe Gamma", host=host, port=80, mac=mac, hostname="bitaxe", **kw)


async def test_migration_sets_version(store):
    assert await store.db.schema_version() >= 1


async def test_device_roundtrip_and_update(store):
    dev = await store.add_device(info(), name="Garage Gamma", tags=["garage"], group="rack1")
    got = await store.get_device(dev.id)
    assert got is not None and got.name == "Garage Gamma" and got.tags == ["garage"] and got.group == "rack1"
    got.name = "Renamed"
    got.alt_hosts = ["10.0.0.6"]
    got.extra["power_override_w"] = 140
    await store.save_device(got)
    again = await store.get_device(dev.id)
    assert again and again.name == "Renamed" and again.alt_hosts == ["10.0.0.6"] and again.extra["power_override_w"] == 140
    assert [d.id for d in await store.list_devices()] == [dev.id]
    assert await store.delete_device(dev.id)
    assert await store.get_device(dev.id) is None


async def test_same_physical_miner_on_two_ips_is_recognised(store):
    # The real-world case seen on the LAN: one Magic Miner answers on .88 and .252 with one MAC.
    dev = await store.add_device(info(host="192.168.9.88", mac="AA:BB:CC:2B:42:E4"))
    found = await store.find_device(info(host="192.168.9.252", mac="aa:bb:cc:2b:42:e4"))
    assert found is not None and found.id == dev.id


async def test_find_device_by_serial_endpoint_and_alt_host(store):
    a = await store.add_device(info(host="10.0.0.1", mac=None, serial="DNA123"))
    assert (await store.find_device(info(host="10.0.0.99", mac=None, serial="DNA123"))).id == a.id  # type: ignore[union-attr]
    assert (await store.find_device(info(host="10.0.0.1", mac=None))).id == a.id  # type: ignore[union-attr]
    a.alt_hosts = ["10.0.0.50"]
    await store.save_device(a)
    assert (await store.find_device(info(host="10.0.0.50", mac=None))).id == a.id  # type: ignore[union-attr]
    assert await store.find_device(info(host="10.9.9.9", mac="11:22:33:44:55:66")) is None


async def test_unique_endpoint_enforced(store):
    await store.add_device(info(host="10.0.0.7", mac="AA:00:00:00:00:01"))
    with pytest.raises(Exception):  # noqa: B017 - sqlite3.IntegrityError
        await store.add_device(info(host="10.0.0.7", mac="AA:00:00:00:00:02"))


async def test_kv_and_counters(store):
    assert await store.kv_get("missing", 5) == 5
    await store.kv_set("a", {"x": [1, 2]})
    assert await store.kv_get("a") == {"x": [1, 2]}
    assert await store.kv_add_float("work", 1.5) == 1.5
    assert await store.kv_add_float("work", 2.0) == 3.5
    await store.kv_delete("a")
    assert await store.kv_get("a") is None


def tele(ts, hashrate, power=20.0, online=True, accepted=0, temp=55.0):
    return Telemetry(ts=ts, online=online, hashrate_hs=hashrate, power_w=power, shares_accepted=accepted, temp_asic_c=temp,
                     efficiency_j_th=(power / (hashrate / 1e12)) if hashrate else None)


async def test_samples_rollup_and_history_fleet(store):
    a = await store.add_device(info(host="10.0.0.1", mac="AA:00:00:00:00:01"))
    b = await store.add_device(info(host="10.0.0.2", mac="AA:00:00:00:00:02"))
    base = (int(time.time()) // 3600) * 3600 - 3600  # start of the previous hour
    rows = []
    for i in range(0, 600, 10):  # 10 minutes, every 10 s
        rows.append(telemetry_to_row(a.id, tele(base + i, 1.0e12, accepted=i)))
        rows.append(telemetry_to_row(b.id, tele(base + i, 3.0e12, power=40.0, accepted=i * 2)))
    await store.samples.write(rows)

    h = await store.samples.history(metrics=["hashrate_hs", "power_w", "efficiency_j_th", "shares_accepted"], start=base, end=base + 600, step=60)
    assert h.source == "samples"  # short span -> raw
    first = next(i for i, v in enumerate(h.series["hashrate_hs"]) if v is not None)
    assert h.series["hashrate_hs"][first] == pytest.approx(4.0e12)  # fleet = sum of devices
    assert h.series["power_w"][first] == pytest.approx(60.0)
    assert h.series["efficiency_j_th"][first] == pytest.approx(60.0 / 4.0)  # total W / total TH/s
    assert h.series["shares_accepted"][first] is not None

    # per device
    hd = await store.samples.history(metrics=["hashrate_hs"], start=base, end=base + 600, step=60, per_device=True)
    assert set(hd.devices) == {a.id, b.id}
    assert hd.devices[a.id]["hashrate_hs"][first] == pytest.approx(1.0e12)

    # longer span uses rollups and gives the same averages
    long = await store.samples.history(metrics=["hashrate_hs"], start=base - 6 * 3600, end=base + 3600, step=3600)
    assert long.source == "samples_1m"
    assert any(v is not None and v == pytest.approx(4.0e12) for v in long.series["hashrate_hs"])


async def test_history_min_max_aggregations(store):
    d = await store.add_device(info())
    base = (int(time.time()) // 60) * 60 - 120
    rows = [telemetry_to_row(d.id, tele(base + i, 1e12 + i * 1e9, temp=50 + i)) for i in range(0, 50, 5)]
    await store.samples.write(rows)
    h = await store.samples.history(metrics=["temp_asic_c", "temp_asic_c:max", "hashrate_hs:min"], start=base, end=base + 120, step=60, per_device=True)
    series = h.devices[d.id]
    assert "temp_asic_c" in series and "temp_asic_c:max" in series and "hashrate_hs:min" in series
    avg = [v for v in series["temp_asic_c"] if v is not None]
    mx = [v for v in series["temp_asic_c:max"] if v is not None]
    assert max(mx) >= max(avg)


async def test_offline_samples_count_against_availability(store):
    d = await store.add_device(info())
    base = (int(time.time()) // 60) * 60 - 300
    rows = [telemetry_to_row(d.id, tele(base + i * 10, 1e12 if i % 2 == 0 else None, online=(i % 2 == 0))) for i in range(20)]
    await store.samples.write(rows)
    avail = await store.samples.availability(base - 60, base + 600)
    assert avail[d.id] == pytest.approx(0.5)


async def test_rollup_is_idempotent_and_prune_respects_retention(store):
    d = await store.add_device(info())
    now = int(time.time())
    old = now - 5 * 86400
    await store.samples.write([telemetry_to_row(d.id, tele(old, 1e12)), telemetry_to_row(d.id, tele(now - 10, 2e12))])
    await store.samples.rollup_window(old, now)
    await store.samples.rollup_window(old, now)  # twice: no duplicates, no errors
    assert await store.db.scalar("SELECT COUNT(*) FROM samples_1m") == 2
    deleted = await store.samples.prune(Retention(raw_days=2, minute_days=90))
    assert deleted["samples"] == 1
    assert await store.db.scalar("SELECT COUNT(*) FROM samples") == 1
    assert await store.db.scalar("SELECT COUNT(*) FROM samples_1m") == 2  # kept (90 day retention)


def test_metric_spec_parsing():
    assert parse_metric_spec("hashrate_hs") == ("hashrate_hs", "avg")
    assert parse_metric_spec("temp_asic_c:max") == ("temp_asic_c", "max")
    assert parse_metric_spec("best_diff") == ("best_diff", "max")  # counters keep their max
    assert parse_metric_spec("fan_pct:max") == ("fan_pct", "avg")  # no max column kept -> falls back
    with pytest.raises(ValueError):
        parse_metric_spec("nope")
    with pytest.raises(ValueError):
        parse_metric_spec("power_w:median")


async def test_history_rejects_bad_ranges(store):
    with pytest.raises(ValueError):
        await store.samples.history(metrics=["hashrate_hs"], start=100, end=50)
    with pytest.raises(ValueError):
        await store.samples.history(metrics=[], start=1, end=2)


async def test_events_filtering_and_ack(store):
    e1 = await store.add_event(Event(type="device_offline", severity=Severity.CRITICAL, title="Garage Gamma is offline", device_id="dev_1"))
    await store.add_event(Event(type="new_best_share", severity=Severity.SUCCESS, title="New best share", device_id="dev_2"))
    await store.add_event(Event(type="info", severity=Severity.INFO, title="hello"))
    assert len(await store.list_events()) == 3
    crit = await store.list_events(min_severity=Severity.WARNING)
    assert [e.type for e in crit] == ["device_offline"]
    assert len(await store.list_events(types=["new_best_share"])) == 1
    assert len(await store.list_events(device_id="dev_1")) == 1
    assert await store.ack_event(e1.id)  # type: ignore[arg-type]
    assert not await store.ack_event(e1.id)  # type: ignore[arg-type]
    assert len(await store.list_events(unacked_only=True)) == 2
    assert await store.ack_all_events() == 2


async def test_channel_secret_is_encrypted_and_write_only(store):
    ch = Channel(id="ch_1", kind="telegram", name="Phone", config={"chat_id": "123"})
    await store.save_channel(ch, secret={"bot_token": "123:ABC"})
    listed = (await store.list_channels())[0]
    assert listed.has_secret is True and "bot_token" not in listed.config
    assert await store.channel_secret("ch_1") == {"bot_token": "123:ABC"}
    raw = await store.db.scalar("SELECT secret_enc FROM channels WHERE id = 'ch_1'")
    assert raw.startswith("enc:v1:") and "123:ABC" not in raw
    # saving without a secret keeps it; an empty dict clears it
    await store.save_channel(ch.model_copy(update={"name": "Phone 2"}))
    assert await store.channel_secret("ch_1") == {"bot_token": "123:ABC"}
    await store.save_channel(ch, secret={})
    assert await store.channel_secret("ch_1") == {}
    assert (await store.list_channels())[0].has_secret is False


async def test_source_secret_roundtrip(store):
    s = Source(id="src_1", kind="bitcoin_core", name="My node", url="http://192.168.1.10:8332")
    await store.save_source(s, secret={"rpc_user": "u", "rpc_password": "p"})
    assert (await store.get_source("src_1")).has_secret is True  # type: ignore[union-attr]
    assert await store.source_secret("src_1") == {"rpc_user": "u", "rpc_password": "p"}


async def test_rules_crud(store):
    rule = AlertRule(id="r1", name="Offline", kind="device_offline", params={"for_s": 120}, severity=Severity.CRITICAL)
    await store.save_rule(rule)
    rule.params["for_s"] = 300
    await store.save_rule(rule)
    got = await store.get_rule("r1")
    assert got and got.params == {"for_s": 300} and got.severity is Severity.CRITICAL
    assert await store.delete_rule("r1") and await store.get_rule("r1") is None


async def test_tokens_and_sessions(store):
    tid, token = await store.create_token("agent", "control")
    assert token.startswith("bsmm_")
    info_ = await store.verify_token(token)
    assert info_ == {"id": tid, "name": "agent", "scope": "control"}
    assert await store.verify_token("bsmm_nope") is None
    raw = await store.db.scalar("SELECT hash FROM tokens")
    assert raw != token and token not in raw  # only the hash is stored
    expired_id, expired = await store.create_token("old", "read", expires_at=time.time() - 5)
    assert await store.verify_token(expired) is None
    assert await store.delete_token(tid)
    sid = await store.create_session(60, "pytest", "127.0.0.1")
    assert await store.verify_session(sid)
    await store.delete_session(sid)
    assert not await store.verify_session(sid)


async def test_blocks_found_deduplicates(store):
    assert await store.add_block_found(hash_="00ab", height=1, ts=1.0, device_id=None, address="bc1q", reward_sats=1, source="node")
    assert not await store.add_block_found(hash_="00ab", height=1, ts=2.0, device_id="d", address="bc1q", reward_sats=1, source="pool")
    assert len(await store.list_blocks_found()) == 1


async def test_audit_redacts_secrets(store):
    await store.add_audit("token:agent", "set_pool", "dev_1", {"url": "x", "stratumPassword": "hunter2", "api_key": "k"}, {"ok": True})
    row = (await store.list_audit())[0]
    assert row["params"]["stratumPassword"] == "***" and row["params"]["api_key"] == "***" and row["params"]["url"] == "x"


async def test_backup_is_a_consistent_copy(store, tmp_path):
    await store.add_device(info())
    target = tmp_path / "copy.db"
    await store.backup_to(target)
    import sqlite3

    con = sqlite3.connect(target)
    assert con.execute("SELECT COUNT(*) FROM devices").fetchone()[0] == 1
    con.close()
