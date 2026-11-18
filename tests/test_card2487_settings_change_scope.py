"""Card #2487 (#162): a settings save only disturbs the parts that use the changed setting.

Saving a theme, a layout or any other setting that no poll reads must not wake the miners or make the outside
sources due again. Settings that a poll does read (``polling``, ``alerts``) still wake the miners; ``network``
still rebuilds the sources. The service loops stay off: each test drives the real settings listeners through
``SettingsService.update`` and checks what they did.
"""

from __future__ import annotations

import asyncio
import logging
import time

import pytest

from bsmm.engine.network import PUBLIC_SOURCE_ID, NetworkService
from bsmm.models import Source
from bsmm.sim.axeos import AxeOSSim

from .test_fleet import add

ADDR = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
PARKED_FOR_S = 3600.0  # a poll time far enough ahead that only a deliberate reset can change it
UNTIL_TIMEOUT_S = 2.0
UNTIL_TICK_S = 0.01

#: saves that no miner poll and no outside source reads
UNRELATED_TO_BOTH = [
    pytest.param({"ui": {"theme": "light"}}, id="ui-theme"),
    pytest.param({"ui": {"hashling_popups": False}}, id="ui-hashling"),
    pytest.param({"ui": {"dashboard": {"widgets": ["a", "b"]}}}, id="ui-dashboard-layout"),
    pytest.param({"units": {"temperature": "f"}}, id="units-temperature"),
    pytest.param({"energy": {"price_per_kwh": 0.2}}, id="energy-price"),
    pytest.param({"mining": {"addresses": [ADDR]}}, id="mining-addresses"),
]


async def until(predicate, timeout_s: float = UNTIL_TIMEOUT_S) -> bool:
    deadline = time.monotonic() + timeout_s
    while not predicate():
        if time.monotonic() > deadline:
            return False
        await asyncio.sleep(UNTIL_TICK_S)
    return True


def park(net: NetworkService) -> float:
    """Push every poller's next poll far into the future; returns that time."""
    parked = time.monotonic() + PARKED_FOR_S
    for p in net._pollers.values():
        p.next_due = parked
    return parked


# --- miners ------------------------------------------------------------------------------------------------------------


@pytest.fixture
async def watched(lan):
    """(ctx, runtime): one miner whose fleet settings listener is registered, as ``Fleet.start`` does."""
    ctx, hosts = lan
    res = await add(ctx, hosts, "miner.test", AxeOSSim("gamma", seed=1, mac="AA:BB:CC:00:00:01"))
    rt = ctx.fleet.runtimes[res.device.id]
    ctx.settings.on_change(ctx.fleet._on_settings_change)
    rt.wake.clear()
    return ctx, rt


@pytest.mark.parametrize("patch", [*UNRELATED_TO_BOTH, pytest.param({"polling": {"interval_s": 10.0}}, id="polling-unchanged")])
async def test_a_save_that_no_poll_reads_does_not_wake_the_miners(watched, patch):
    ctx, rt = watched
    await ctx.settings.update(patch)
    assert not rt.wake.is_set()


@pytest.mark.parametrize(
    "patch",
    [
        pytest.param({"polling": {"interval_s": 20.0}}, id="polling-interval"),
        pytest.param({"polling": {"offline_after_failures": 5}}, id="polling-offline-after"),
        pytest.param({"alerts": {"temp_crit_c": 90.0}}, id="alerts-temp-crit"),
        pytest.param({"alerts": {"vr_temp_warn_c": 90.0}}, id="alerts-vr-temp"),
    ],
)
async def test_a_changed_polling_or_alert_setting_wakes_the_miners(watched, patch):
    ctx, rt = watched
    await ctx.settings.update(patch)
    assert rt.wake.is_set()


async def test_a_changed_concurrency_replaces_the_semaphore_and_an_unrelated_save_keeps_it(watched):
    ctx, rt = watched
    semaphore = ctx.fleet._sem
    await ctx.settings.update({"ui": {"theme": "light"}})
    assert ctx.fleet._sem is semaphore
    await ctx.settings.update({"polling": {"concurrency": 5}})
    assert ctx.fleet._sem is not semaphore
    assert rt.wake.is_set()


# --- outside sources ---------------------------------------------------------------------------------------------------


async def no_loop() -> None:
    """Stands in for the service loop, so only the settings listener is under test."""


@pytest.fixture
async def net(lan, monkeypatch):
    """A started network service (public source, no loop) over the test context's settings."""
    ctx, _ = lan
    service = NetworkService(ctx.store, ctx.settings, ctx.bus, ctx.events, ctx.http, offline=False)
    monkeypatch.setattr(service, "_loop", no_loop)
    await service.start()
    yield service
    await service.stop()


def count_reloads(net: NetworkService, monkeypatch) -> list[int]:
    """Record every ``reload_sources`` call at the moment it is made, then run the real one."""
    calls: list[int] = []
    original = net.reload_sources

    def spy():
        calls.append(1)
        return original()

    monkeypatch.setattr(net, "reload_sources", spy)
    return calls


@pytest.mark.parametrize("patch", [*UNRELATED_TO_BOTH, pytest.param({"polling": {"interval_s": 20.0}}, id="polling-interval")])
async def test_a_save_outside_the_network_section_leaves_the_sources_alone(lan, net, monkeypatch, patch):
    ctx, _ = lan
    reloads = count_reloads(net, monkeypatch)
    pub = net._pollers[PUBLIC_SOURCE_ID]
    parked = park(net)
    await ctx.settings.update(patch)
    assert reloads == []
    assert net._pollers[PUBLIC_SOURCE_ID] is pub and pub.next_due == parked


async def test_a_currency_change_refreshes_the_price_without_rebuilding_the_sources(lan, net, monkeypatch):
    ctx, _ = lan
    reloads = count_reloads(net, monkeypatch)
    pub = net._pollers[PUBLIC_SOURCE_ID]
    park(net)
    await ctx.settings.update({"units": {"currency": "EUR"}})  # the merged price follows the currency
    assert reloads == []
    assert net._pollers[PUBLIC_SOURCE_ID] is pub and pub.next_due == 0.0


@pytest.mark.parametrize(
    "patch",
    [
        pytest.param({"network": {"use_public_apis": False}}, id="use-public-apis"),
        pytest.param({"network": {"mempool_url": "http://mempool.home:3006/"}}, id="mempool-url"),
        pytest.param({"network": {"price_source": "manual", "manual_btc_price": 50000.0}}, id="manual-price"),
    ],
)
async def test_a_changed_network_setting_still_reloads_the_sources(lan, net, monkeypatch, patch):
    ctx, _ = lan
    reloads = count_reloads(net, monkeypatch)
    await ctx.settings.update(patch)
    assert len(reloads) == 1


async def test_turning_public_lookups_off_removes_the_public_source(lan, net):
    ctx, _ = lan
    await ctx.settings.update({"network": {"use_public_apis": False}})
    assert await until(lambda: net._pollers == {})


async def test_a_new_mempool_address_replaces_the_public_source_and_polls_it_at_once(lan, net):
    ctx, _ = lan
    old = net._pollers[PUBLIC_SOURCE_ID]
    park(net)
    await ctx.settings.update({"network": {"mempool_url": "http://mempool.home:3006/"}})
    assert await until(lambda: net._pollers[PUBLIC_SOURCE_ID] is not old)
    replaced = net._pollers[PUBLIC_SOURCE_ID]
    assert replaced.source.url == "http://mempool.home:3006" and replaced.next_due == 0.0


async def test_a_price_setting_makes_the_kept_sources_due_so_the_figure_changes_at_once(lan, net):
    ctx, _ = lan
    pub = net._pollers[PUBLIC_SOURCE_ID]
    park(net)
    await ctx.settings.update({"network": {"price_source": "manual", "manual_btc_price": 50000.0}})
    assert await until(lambda: pub.next_due == 0.0)
    assert net._pollers[PUBLIC_SOURCE_ID] is pub


async def test_a_failed_reload_is_logged_and_does_not_fail_the_save(lan, net, monkeypatch, caplog):
    ctx, _ = lan

    async def failing_reload() -> None:
        raise RuntimeError("database is locked")

    monkeypatch.setattr(net, "reload_sources", failing_reload)
    with caplog.at_level(logging.ERROR, logger="bsmm.engine.network"):
        saved = await ctx.settings.update({"network": {"use_public_apis": False}})
    assert saved.network.use_public_apis is False  # the setting is saved either way
    assert any(
        r.name == "bsmm.engine.network" and r.levelno >= logging.ERROR and r.exc_info and "database is locked" in str(r.exc_info[1])
        for r in caplog.records
    )


# --- reload_sources itself ---------------------------------------------------------------------------------------------


async def test_reload_sources_only_makes_new_or_changed_sources_due(lan):
    ctx, _ = lan
    net = ctx.network
    a = await net.add_source("public_pool", "Pool A", "http://pool.test:2019", None, None)
    b = await net.add_source("mempool_space", "Mempool B", "http://mempool.test", None, None)
    parked = park(net)
    await ctx.store.save_source(a.model_copy(update={"name": "Pool A (renamed)"}))
    c = Source(id="src_new", kind="public_pool", name="Pool C", url="http://poolc.test:2019")
    await ctx.store.save_source(c)
    await net.reload_sources()
    assert net._pollers[a.id].next_due == 0.0  # changed: rebuilt, polled promptly
    assert net._pollers[c.id].next_due == 0.0  # new: polled promptly
    assert net._pollers[b.id].next_due == parked  # unchanged: keeps its schedule


async def test_the_public_source_keeps_its_schedule_until_its_address_changes(lan):
    ctx, _ = lan
    net = NetworkService(ctx.store, ctx.settings, ctx.bus, ctx.events, ctx.http, offline=False)
    await net.reload_sources()
    pub = net._pollers[PUBLIC_SOURCE_ID]
    parked = park(net)
    await net.reload_sources()
    assert net._pollers[PUBLIC_SOURCE_ID] is pub and pub.next_due == parked
    await ctx.settings.update({"network": {"mempool_url": "http://mempool.home:3006"}})  # no listener on this service
    await net.reload_sources()
    assert net._pollers[PUBLIC_SOURCE_ID] is not pub and net._pollers[PUBLIC_SOURCE_ID].next_due == 0.0


async def test_removing_a_source_still_makes_the_remaining_ones_due(api):
    c, ctx, _ = api
    a = await ctx.network.add_source("public_pool", "Pool A", "http://pool.test:2019", None, None)
    b = await ctx.network.add_source("mempool_space", "Mempool B", "http://mempool.test", None, None)
    park(ctx.network)
    assert (await c.delete(f"/api/v1/sources/{a.id}")).status_code == 200
    assert list(ctx.network._pollers) == [b.id]
    assert ctx.network._pollers[b.id].next_due == 0.0  # the merged picture drops the removed source on the next round
