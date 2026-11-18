"""Issue #161: an Avalon's chip serial (DNA) is checked on every poll, like AxeOS's identity.

Discovery saves the estats ``DNA`` as the miner's serial. If two Avalons swap addresses (or a unit is
replaced) the old miner's record must not silently show the other unit's readings. A contradicting DNA is
an ordinary failed poll (#92); a missing serial, a missing DNA or a failed ``estats`` keeps today's behaviour.
"""
from typing import Any

import pytest

from bsmm.drivers.base import IdentityMismatch, Unreachable
from bsmm.drivers.cgminer import CgminerDriver
from bsmm.models import DeviceInfo, DeviceStatus, ProbeResult
from bsmm.net import make_http_client
from bsmm.sim.cgminer import CgminerSim

from .test_fleet import events, poll

SAVED_DNA = "0123456789abcdef"  # the DNA the Avalon Nano 3 simulator reports by default
OTHER_DNA = "fedcba9876543210"
SIM_DNA_FIELD = f"DNA[{SAVED_DNA}]"


class DnaSim(CgminerSim):
    """The Avalon simulator with a DNA the test can change, drop or break while the miner "runs"."""

    def __init__(self) -> None:
        super().__init__("avalon_nano3", seed=1)
        self.dna: str | None = SAVED_DNA
        self.estats_fails = False

    def reply(self, command: str) -> dict[str, Any]:
        out = super().reply(command)
        if command != "estats":
            return out
        if self.estats_fails:
            return {"STATUS": [{"STATUS": "E", "Code": 14, "Msg": "Invalid command"}], "id": 1}
        element = out["STATS"][0]
        replacement = f"DNA[{self.dna}]" if self.dna else ""
        element["MM ID0"] = element["MM ID0"].replace(SIM_DNA_FIELD, replacement)
        return out


class EstatsDownDriver(CgminerDriver):
    """A driver whose ``estats`` call raises, while summary and pools still answer."""

    async def _call(self, command: str) -> dict[str, Any]:
        if command == "estats":
            raise Unreachable("estats did not answer")
        return await super()._call(command)


def avalon_info(sim: CgminerSim, serial: str | None) -> DeviceInfo:
    return DeviceInfo(driver="cgminer", family="avalon", model="Avalon Nano 3", host="127.0.0.1",
                      port=sim.port, serial=serial, extra={"monitor_only": True})


@pytest.fixture
async def sim():
    s = await DnaSim().start()
    yield s
    await s.stop()


async def test_poll_refuses_a_different_dna(sim):
    sim.dna = OTHER_DNA
    info = avalon_info(sim, SAVED_DNA)
    async with make_http_client() as client:
        driver = CgminerDriver("127.0.0.1", sim.port, client=client, info=info)
        with pytest.raises(IdentityMismatch, match="identity"):
            await driver.poll()
    assert driver.info is info and info.serial == SAVED_DNA


async def test_poll_accepts_the_same_dna_without_an_extra_request(sim):
    async with make_http_client() as client:
        driver = CgminerDriver("127.0.0.1", sim.port, client=client, info=avalon_info(sim, SAVED_DNA))
        telemetry = await driver.poll()
    assert telemetry.online and telemetry.hashrate_hs == pytest.approx(3900e9)
    assert sim.commands == ["summary", "pools", "estats"]


async def test_poll_without_a_dna_in_estats_keeps_working(sim):
    sim.dna = None
    async with make_http_client() as client:
        driver = CgminerDriver("127.0.0.1", sim.port, client=client, info=avalon_info(sim, SAVED_DNA))
        telemetry = await driver.poll()
    assert telemetry.online and telemetry.pools


async def test_poll_with_an_error_reply_to_estats_keeps_working(sim):
    sim.dna = OTHER_DNA  # would contradict, but the failed command carries no DNA to compare
    sim.estats_fails = True
    async with make_http_client() as client:
        driver = CgminerDriver("127.0.0.1", sim.port, client=client, info=avalon_info(sim, SAVED_DNA))
        telemetry = await driver.poll()
    assert telemetry.online and telemetry.hashrate_hs is not None


async def test_poll_with_a_failed_estats_call_keeps_working(sim):
    sim.dna = OTHER_DNA
    async with make_http_client() as client:
        driver = EstatsDownDriver("127.0.0.1", sim.port, client=client, info=avalon_info(sim, SAVED_DNA))
        telemetry = await driver.poll()
    assert telemetry.online


@pytest.mark.parametrize("saved", [None, ""])
async def test_poll_without_a_saved_serial_is_endpoint_only(sim, saved):
    sim.dna = OTHER_DNA
    async with make_http_client() as client:
        driver = CgminerDriver("127.0.0.1", sim.port, client=client, info=avalon_info(sim, saved))
        telemetry = await driver.poll()
    assert telemetry.online and telemetry.hashrate_hs == pytest.approx(3900e9)


async def test_other_cgminer_families_are_not_compared():
    antminer = await CgminerSim("antminer_s19", seed=2).start()
    try:
        info = DeviceInfo(driver="cgminer", family="antminer", model="Antminer S19j Pro", host="127.0.0.1",
                          port=antminer.port, serial="saved-board-serial")
        async with make_http_client() as client:
            telemetry = await CgminerDriver("127.0.0.1", antminer.port, client=client, info=info).poll()
        assert telemetry.online
        assert antminer.commands == ["summary", "pools", "stats"]
    finally:
        await antminer.stop()


# -- fleet: a mismatch is a failed poll, the miner goes offline only after the normal threshold (#92) ----------


async def avalon_runtime(ctx, sim):
    result = await ctx.fleet.add_from_probe(ProbeResult(info=avalon_info(sim, SAVED_DNA)))
    rt = await poll(ctx, result.device.id)
    assert rt.status == DeviceStatus.ONLINE and rt.failures == 0
    return result.device.id, rt


async def test_swapped_avalon_goes_offline_only_after_the_threshold(lan, sim):
    ctx, _ = lan
    did, rt = await avalon_runtime(ctx, sim)
    threshold = ctx.settings.current.polling.offline_after_failures
    sim.dna = OTHER_DNA  # another unit now answers at this address
    for expected_failures in range(1, threshold):
        await poll(ctx, did)
        assert rt.status == DeviceStatus.ONLINE and rt.failures == expected_failures
        assert "identity" in (rt.last_error or "")
    await poll(ctx, did)
    assert rt.status == DeviceStatus.OFFLINE and "identity" in (rt.last_error or "")
    offline = await ctx.store.list_events(types=["device_offline"])
    assert len(offline) == 1 and "identity changed" in (offline[0].body or "")


async def test_one_odd_avalon_reading_is_not_an_outage(lan, sim):
    ctx, _ = lan
    did, rt = await avalon_runtime(ctx, sim)
    sim.dna = OTHER_DNA
    await poll(ctx, did)
    assert rt.status == DeviceStatus.ONLINE and rt.failures == 1
    sim.dna = SAVED_DNA
    await poll(ctx, did)
    assert rt.status == DeviceStatus.ONLINE and rt.failures == 0 and rt.last_error is None
    kinds = await events(ctx)
    assert "device_offline" not in kinds and "device_online" not in kinds
