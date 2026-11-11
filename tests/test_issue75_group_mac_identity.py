"""Issue #75: a placeholder or group MAC is unknown, never a different miner, and never authorizes control."""
import json
from pathlib import Path

import httpx
import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from bsmm.drivers import axeos
from bsmm.drivers.axeos import AxeOSDriver, build_info, normalize_mac
from bsmm.drivers.base import ActionFailed, DriverError, IdentityMismatch
from bsmm.models import DeviceInfo, ProbeResult
from bsmm.sim.axeos import AxeOSSim

from .test_foundation_fleet import miner

SAVED_MAC = "30:00:00:00:00:01"
INVALID_MACS = ["00:00:00:00:00:00", "FF:FF:FF:FF:FF:FF", "01:00:5E:00:00:01",
                "FD:E0:CC:3F:A0:01", "not-a-mac", "   ", 123]
FIXTURE = Path(__file__).parent / "fixtures" / "axeos" / "magicminer_bg02_v1.0.0.json"


@pytest.fixture
def bg02():
    return json.loads(FIXTURE.read_text())


@pytest.fixture
async def firmware(bg02):
    calls = []

    def reply(request):
        calls.append((request.method, request.url.path))
        assert request.method == "GET", "the driver must not write during identity checks"
        if request.url.path == "/api/system/info":
            return httpx.Response(200, json=bg02)
        assert request.url.path == "/api/system/asic"
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
        yield client, calls


@pytest.mark.parametrize("mac", INVALID_MACS)
def test_unusable_mac_is_not_an_identity(mac):
    assert normalize_mac(mac) is None


@pytest.mark.parametrize("mac,expected", [
    ("00:11:22:33:44:55", "00:11:22:33:44:55"),
    ("02:11:22:33:44:55", "02:11:22:33:44:55"),
    ("32:00:00:00:00:01", "32:00:00:00:00:01"),
    (" aa-bb-cc-00-00-01 ", "AA:BB:CC:00:00:01"),
    ("FE:FF:FF:FF:FF:FF", "FE:FF:FF:FF:FF:FF"),
])
def test_individual_mac_preserves_local_bit(mac, expected):
    assert normalize_mac(mac) == expected


@pytest.mark.parametrize("mac", INVALID_MACS)
async def test_bg02_unusable_mac_polls_without_changing_saved_identity(bg02, firmware, mac):
    client, calls = firmware
    info = build_info("miner.test", 80, {**bg02, "macAddr": SAVED_MAC})
    before = info.model_dump()
    driver = AxeOSDriver("miner.test", 80, client=client, info=info)
    bg02["macAddr"] = mac
    for _ in range(3):
        telemetry = await driver.poll()
        assert telemetry.online and telemetry.firmware == "v1.0.0"
        assert telemetry.hashrate_hs == pytest.approx(7.314046e12, rel=1e-6)
        assert telemetry.temp_asic_c == pytest.approx(58.8125)
    assert info.model_dump() == before and driver.info is info
    assert build_info("miner.test", 80, bg02).mac is None
    assert calls == [("GET", "/api/system/info")] * 3


@pytest.mark.parametrize("operation", ["poll", "refresh_info", "verify_identity"])
@pytest.mark.parametrize("other", ["30:00:00:00:00:02", "32:00:00:00:00:01"])
async def test_valid_mac_conflict_still_refuses(bg02, firmware, operation, other):
    client, _ = firmware
    info = build_info("miner.test", 80, {**bg02, "macAddr": SAVED_MAC})
    driver = AxeOSDriver("miner.test", 80, client=client, info=info)
    bg02["macAddr"] = other
    with pytest.raises(IdentityMismatch, match="identity"):
        await getattr(driver, operation)()
    assert driver.info is info and info.mac == SAVED_MAC


@pytest.mark.parametrize("operation", ["poll", "refresh_info"])
@pytest.mark.parametrize("saved", INVALID_MACS[:4])
async def test_legacy_unusable_saved_mac_is_only_normalized_for_comparison(bg02, firmware, operation, saved):
    client, _ = firmware
    info = build_info("miner.test", 80, bg02).model_copy(update={"mac": saved, "serial": "saved-serial"})
    before = info.model_dump()
    driver = AxeOSDriver("miner.test", 80, client=client, info=info)
    result = await getattr(driver, operation)()
    assert result is not None
    assert info.model_dump() == before
    if operation == "poll":
        assert driver.info is info


@pytest.mark.parametrize("operation", ["poll", "refresh_info", "verify_identity"])
@pytest.mark.parametrize("saved_mac", [SAVED_MAC, "00:00:00:00:00:00"])
async def test_serial_conflict_survives_mac_normalization(bg02, firmware, monkeypatch, operation, saved_mac):
    # AxeOS currently has no serial parser. Supply DeviceInfo at that boundary to
    # prove comparison-only MAC normalization cannot discard a serial conflict.
    client, _ = firmware
    info = build_info("miner.test", 80, bg02).model_copy(update={"mac": saved_mac, "serial": "original"})
    observed = info.model_copy(update={"mac": None, "serial": "replacement"})
    monkeypatch.setattr(axeos, "build_info", lambda *args: observed)
    driver = AxeOSDriver("miner.test", 80, client=client, info=info)
    with pytest.raises(IdentityMismatch, match="identity"):
        await getattr(driver, operation)()
    assert driver.info is info and info.serial == "original"


@pytest.mark.parametrize("mac", INVALID_MACS)
@pytest.mark.parametrize("saved", [SAVED_MAC, None])
async def test_precontrol_fresh_read_refuses_unusable_mac(bg02, firmware, mac, saved):
    client, calls = firmware
    info = build_info("miner.test", 80, {**bg02, "macAddr": saved})
    driver = AxeOSDriver("miner.test", 80, client=client, info=info)
    # A preceding good poll must not authorize a later unusable identity.
    bg02["macAddr"] = saved
    await driver.poll()
    bg02["macAddr"] = mac
    with pytest.raises(ActionFailed, match="unusable MAC"):
        await driver.verify_identity()
    assert calls == [("GET", "/api/system/info")] * 2


@pytest.mark.parametrize("missing", ["absent", None, ""])
@pytest.mark.parametrize("saved", [SAVED_MAC, None])
async def test_missing_identity_keeps_previous_endpoint_compatibility(bg02, firmware, missing, saved):
    client, calls = firmware
    info = build_info("miner.test", 80, {**bg02, "macAddr": saved})
    driver = AxeOSDriver("miner.test", 80, client=client, info=info)
    if missing == "absent":
        bg02.pop("macAddr")
    else:
        bg02["macAddr"] = missing
    assert (await driver.poll()).online
    await driver.verify_identity()
    assert calls == [("GET", "/api/system/info")] * 2


async def test_fleet_bg02_monitoring_recovers_but_control_never_writes(lan, bg02):
    ctx, hosts = lan
    calls = []

    async def reply(request):
        calls.append((request.method, request.url.path))
        return JSONResponse(bg02 if request.method == "GET" else {})

    hosts["miner.test"] = Starlette(routes=[
        Route("/api/system/info", reply),
        Route("/api/system/restart", reply, methods=["POST"]),
    ])
    info = build_info("miner.test", 80, {**bg02, "macAddr": SAVED_MAC})
    device = (await ctx.fleet.add_from_probe(ProbeResult(info=info))).device
    bg02["macAddr"] = "FD:E0:CC:3F:A0:01"
    await ctx.fleet.poll_now(device.id)
    view = ctx.fleet.view(device.id)
    assert view.status == "online" and view.last_error is None
    assert view.telemetry.hashrate_hs == pytest.approx(7.314046e12, rel=1e-6)
    with pytest.raises(ActionFailed, match="unusable MAC"):
        await ctx.fleet.run_action(device.id, "restart")
    assert calls == [("GET", "/api/system/info")] * 2
    assert (await ctx.store.get_device(device.id)).mac == SAVED_MAC
    assert ctx.fleet.runtimes[device.id].device.mac == SAVED_MAC


@pytest.mark.parametrize("reported", ["00:00:00:00:00:00", "FF:FF:FF:FF:FF:FF", "01:00:5E:00:00:01", "FD:E0:CC:3F:A0:01"])
async def test_fleet_zero_and_group_mac_miner_stays_online_and_refuses_control(lan, reported):
    ctx, hosts = lan
    did, sim = await miner(ctx, hosts)
    sim.mac = reported
    for _ in range(3):
        await ctx.fleet.poll_now(did)
    view = ctx.fleet.view(did)
    assert view.status == "online" and view.last_error is None
    ctx.settings.current.safety.allow_control = True
    with pytest.raises(ActionFailed, match="unusable MAC"):
        await ctx.fleet.run_action(did, "restart")
    assert sim.restarts == 0
    assert (await ctx.store.get_device(did)).mac == "AA:BB:CC:00:00:01"


async def test_fleet_stored_group_mac_does_not_raise_identity_changed(lan):
    ctx, hosts = lan
    hosts["miner.test"] = AxeOSSim("gamma", seed=1, mac="AA:BB:CC:00:00:01").app()
    # A record saved by an older release, which kept the group MAC as if it were an identity.
    legacy = DeviceInfo(driver="axeos", family="bitaxe", model="Bitaxe Gamma", host="miner.test", port=80,
                        mac="FD:E0:CC:3F:A0:01")
    did = (await ctx.fleet.add_from_probe(ProbeResult(info=legacy))).device.id
    for _ in range(3):
        await ctx.fleet.poll_now(did)
    view = ctx.fleet.view(did)
    assert view.status == "online" and view.last_error is None
    assert (await ctx.store.get_device(did)).mac == "FD:E0:CC:3F:A0:01"
    assert ctx.fleet.runtimes[did].device.mac == "FD:E0:CC:3F:A0:01"


@pytest.mark.parametrize("other", ["AA:BB:CC:00:00:02", "02:11:22:33:44:55"])
async def test_fleet_truly_different_miner_is_still_rejected(lan, other):
    ctx, hosts = lan
    did, sim = await miner(ctx, hosts)
    await ctx.fleet.poll_now(did)
    sim.mac = other
    for _ in range(3):
        await ctx.fleet.poll_now(did)
    view = ctx.fleet.view(did)
    assert view.status != "online" and view.last_error and "identity" in view.last_error
    ctx.settings.current.safety.allow_control = True
    with pytest.raises(DriverError, match="identity"):
        await ctx.fleet.run_action(did, "restart")
    assert sim.restarts == 0


async def test_fleet_locally_administered_unicast_mac_is_a_working_identity(lan):
    ctx, hosts = lan
    did, sim = await miner(ctx, hosts, mac="02:11:22:33:44:55")
    assert (await ctx.store.get_device(did)).mac == "02:11:22:33:44:55"
    await ctx.fleet.poll_now(did)
    assert ctx.fleet.view(did).status == "online"
    ctx.settings.current.safety.allow_control = True
    assert (await ctx.fleet.run_action(did, "restart"))["ok"] and sim.restarts == 1
    sim.mac = "06:11:22:33:44:55"  # differs only in a locally administered address bit
    for _ in range(3):
        await ctx.fleet.poll_now(did)
    assert ctx.fleet.view(did).status != "online"
    with pytest.raises(DriverError, match="identity"):
        await ctx.fleet.run_action(did, "restart")
    assert sim.restarts == 1
