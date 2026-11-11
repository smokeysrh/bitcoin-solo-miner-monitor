"""Issue #92: one odd identity reading must not flip a working miner offline.

A mismatch is an ordinary failed poll. The miner is only treated as replaced when the mismatch persists for
``offline_after_failures`` consecutive polls, and a replaced miner still cannot be controlled.
"""
import pytest

from bsmm.drivers.base import DriverError
from bsmm.models import DeviceStatus

from .test_fleet import events, poll
from .test_foundation_fleet import miner

SAVED_MAC = "AA:BB:CC:00:00:01"  # the address the `miner` helper adopts
OTHER_MAC = "AA:BB:CC:00:00:02"


async def test_single_mismatched_poll_does_not_flip_the_miner_offline(lan):
    ctx, hosts = lan
    did, sim = await miner(ctx, hosts)
    rt = await poll(ctx, did)
    assert rt.status == DeviceStatus.ONLINE
    sim.mac = OTHER_MAC
    await poll(ctx, did)
    assert rt.status == DeviceStatus.ONLINE and rt.failures == 1
    assert "identity" in (rt.last_error or "")
    sim.mac = SAVED_MAC
    await poll(ctx, did)
    assert rt.status == DeviceStatus.ONLINE and rt.failures == 0 and rt.last_error is None
    kinds = await events(ctx)
    assert "device_offline" not in kinds and "device_online" not in kinds


async def test_repeated_isolated_mismatches_never_accumulate(lan):
    ctx, hosts = lan
    did, sim = await miner(ctx, hosts)
    rt = await poll(ctx, did)
    for _ in range(5):  # a good poll in between resets the count: the mismatches are not consecutive
        sim.mac = OTHER_MAC
        await poll(ctx, did)
        sim.mac = SAVED_MAC
        await poll(ctx, did)
    assert rt.status == DeviceStatus.ONLINE
    assert "device_offline" not in await events(ctx)


async def test_two_consecutive_mismatches_are_still_tolerated(lan):
    ctx, hosts = lan
    did, sim = await miner(ctx, hosts)
    rt = await poll(ctx, did)
    assert ctx.settings.current.polling.offline_after_failures == 3
    sim.mac = OTHER_MAC
    await poll(ctx, did)
    await poll(ctx, did)
    assert rt.status == DeviceStatus.ONLINE and rt.failures == 2


async def test_persistent_mismatch_is_flagged_after_the_threshold(lan):
    ctx, hosts = lan
    did, sim = await miner(ctx, hosts)
    rt = await poll(ctx, did)
    sim.mac = OTHER_MAC
    threshold = ctx.settings.current.polling.offline_after_failures
    for _ in range(threshold - 1):
        await poll(ctx, did)
        assert rt.status == DeviceStatus.ONLINE
    await poll(ctx, did)
    assert rt.status == DeviceStatus.OFFLINE
    assert "identity" in (rt.last_error or "")
    offline = await ctx.store.list_events(types=["device_offline"])
    assert len(offline) == 1 and "identity changed" in (offline[0].body or "")
    # Replacement protection for control is unchanged.
    ctx.settings.current.safety.allow_control = True
    with pytest.raises(DriverError, match="identity"):
        await ctx.fleet.run_action(did, "restart")
    assert sim.restarts == 0


@pytest.mark.parametrize("transient", ["", None, "00:00:00:00:00:00", "FD:E0:CC:3F:A0:01"])
async def test_transient_empty_or_unusable_mac_is_not_a_mismatch(lan, transient):
    ctx, hosts = lan
    did, sim = await miner(ctx, hosts)
    rt = await poll(ctx, did)
    sim.mac = transient
    for _ in range(5):  # even a long run is compatible, not a failure
        await poll(ctx, did)
        assert rt.status == DeviceStatus.ONLINE and rt.failures == 0 and rt.last_error is None
    assert "device_offline" not in await events(ctx)
