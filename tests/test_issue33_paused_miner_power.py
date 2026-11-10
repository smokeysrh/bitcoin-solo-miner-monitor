"""A paused miner draws no power: it must not make the electricity cost look incomplete or unknown (#33 review)."""
from bsmm.engine.fleet import DeviceRuntime, build_summary
from bsmm.engine.network import NetworkState
from bsmm.engine.odds import build_odds
from bsmm.models import Device, DeviceStatus, Telemetry
from bsmm.settings import Settings
from bsmm.sim.axeos import AxeOSSim

NET = NetworkState(difficulty=1e14, btc_price=80_000.0)


async def _add(ctx, hosts, host: str, sim: AxeOSSim, *, paused: bool):
    hosts[host] = sim.app()
    # only the AxeOS driver: the cgminer driver would open real sockets to the fake host names
    res = await ctx.fleet.add_by_host(host, drivers=["axeos"])
    sim.paused = paused
    await ctx.fleet._poll_once(ctx.fleet.runtimes[res.device.id])
    return ctx.fleet.runtimes[res.device.id]


async def test_paused_miner_is_not_counted_as_missing_power(lan):
    ctx, hosts = lan
    running = await _add(ctx, hosts, "run.test", AxeOSSim("gamma", seed=1, mac="AA:BB:CC:33:00:01"), paused=False)
    paused = await _add(ctx, hosts, "pause.test", AxeOSSim("gamma", seed=2, mac="AA:BB:CC:33:00:02"), paused=True)
    assert running.status == DeviceStatus.ONLINE and paused.status == DeviceStatus.PAUSED
    summary = ctx.fleet.summary(fresh=True)
    assert summary.devices_paused == 1
    assert summary.devices_without_power == 0
    eco = build_odds(summary, NET, Settings())["economics"]
    assert eco["power_complete"] is True
    assert eco["cost_note"] is None
    assert eco["cost_per_day"] is not None and eco["cost_per_day"] > 0


async def test_all_paused_fleet_costs_nothing_instead_of_unknown(lan):
    ctx, hosts = lan
    await _add(ctx, hosts, "p1.test", AxeOSSim("gamma", seed=3, mac="AA:BB:CC:33:00:03"), paused=True)
    await _add(ctx, hosts, "p2.test", AxeOSSim("gamma", seed=4, mac="AA:BB:CC:33:00:04"), paused=True)
    summary = ctx.fleet.summary(fresh=True)
    assert summary.devices_paused == 2
    assert summary.devices_without_power == 0
    assert summary.power_w == 0.0
    eco = build_odds(summary, NET, Settings())["economics"]
    assert eco["cost_per_day"] == 0.0
    assert eco["power_complete"] is True
    assert eco["cost_note"] is None


def test_paused_miner_does_not_hide_an_online_miner_that_lacks_power():
    def runtime(name: str, status: DeviceStatus, power_w: float | None) -> DeviceRuntime:
        device = Device(id=name, name=name, driver="axeos", family="bitaxe", model="m", host=name, port=80)
        return DeviceRuntime(device=device, status=status, telemetry=Telemetry(hashrate_hs=1e12, power_w=power_w))

    summary = build_summary(
        [
            runtime("a", DeviceStatus.ONLINE, 20.0),
            runtime("b", DeviceStatus.ONLINE, None),
            runtime("c", DeviceStatus.PAUSED, None),
        ],
        Settings(),
    )
    assert summary.devices_without_power == 1
