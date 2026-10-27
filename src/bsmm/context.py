"""Wires every service together and owns the application's start-up / shutdown."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from dataclasses import dataclass, field

import httpx

from bsmm import __version__
from bsmm.auth import AuthService
from bsmm.config import RuntimeConfig
from bsmm.engine.alerts import AlertEngine
from bsmm.engine.bus import EventBus
from bsmm.engine.discovery import DiscoveryService
from bsmm.engine.events import EventLog
from bsmm.engine.fleet import Fleet
from bsmm.engine.network import NetworkService
from bsmm.net import make_http_client
from bsmm.notify.dispatcher import Notifier
from bsmm.settings import SettingsService
from bsmm.storage.store import Store
from bsmm.updates import check_for_update

log = logging.getLogger(__name__)


@dataclass
class AppContext:
    config: RuntimeConfig
    store: Store
    settings: SettingsService
    bus: EventBus
    events: EventLog
    http: httpx.AsyncClient
    fleet: Fleet
    network: NetworkService
    notifier: Notifier
    alerts: AlertEngine
    discovery: DiscoveryService
    auth: AuthService
    started_at: float = field(default_factory=time.time)
    _bg: list[asyncio.Task[None]] = field(default_factory=list)

    @classmethod
    async def create(cls, config: RuntimeConfig, *, store: Store | None = None, http: httpx.AsyncClient | None = None) -> AppContext:
        if store is None:
            store = await Store.open_memory() if config.demo else await Store.open(config)
        settings = SettingsService(store)
        await settings.load()
        bus = EventBus()
        events = EventLog(store, bus)
        http = http or make_http_client()
        fleet = Fleet(store, settings, bus, events, http, demo=config.demo)
        network = NetworkService(store, settings, bus, events, http, offline=config.offline, demo=config.demo)
        notifier = Notifier(store, settings, http, events)
        alerts = AlertEngine(store, settings, bus, fleet, network, notifier)
        discovery = DiscoveryService(store, bus, events, fleet, http)
        auth = AuthService(store)
        ctx = cls(config, store, settings, bus, events, http, fleet, network, notifier, alerts, discovery, auth)
        fleet.difficulty_provider = network.difficulty
        network.watch_addresses = fleet.all_addresses
        return ctx

    async def start(self) -> None:
        cfg = self.settings.current
        if cfg.general.first_run_at is None:
            await self.settings.update({"general": {"first_run_at": time.time()}})
        await self._apply_env_overrides()
        await self.fleet.start()
        await self.network.start()
        await self.alerts.start()
        self._bg = [
            asyncio.create_task(self._feed_device_network_facts(), name="device-network-facts"),
            asyncio.create_task(self._heal_loop(), name="heal-moved-devices"),
            asyncio.create_task(self._update_loop(), name="update-check"),
        ]
        log.info("Solo Miner Monitor %s started (%d miner(s))", __version__, len(self.fleet.runtimes))

    async def stop(self) -> None:
        for t in self._bg:
            t.cancel()
        await asyncio.gather(*self._bg, return_exceptions=True)
        await self.alerts.stop()
        await self.network.stop()
        await self.fleet.stop()
        self.bus.close_all()
        await self.http.aclose()
        await self.store.close()

    async def _apply_env_overrides(self) -> None:
        if self.config.auth_mode in ("none", "password") and self.settings.current.auth.mode != self.config.auth_mode:
            await self.settings.update({"auth": {"mode": self.config.auth_mode}})
        if self.config.admin_password and not await self.auth.has_password():
            await self.auth.set_password(self.config.admin_password)
            if self.settings.current.auth.mode == "none" and self.config.auth_mode is None:
                await self.settings.update({"auth": {"mode": "password"}})

    async def _feed_device_network_facts(self) -> None:
        """Firmware 2.x reports block height + network difficulty itself: a last-resort data source."""
        while True:
            await asyncio.sleep(15)
            best_h, best_d = None, None
            for rt in self.fleet.runtimes.values():
                t = rt.telemetry
                if t and t.network_difficulty:
                    best_d = t.network_difficulty
                    best_h = max(best_h or 0, t.block_height or 0) or None
            if best_d:
                self.network.set_device_snapshot(best_h, best_d)

    async def _heal_loop(self) -> None:
        while True:
            await asyncio.sleep(600)
            with contextlib.suppress(Exception):
                await self.discovery.heal_moved_devices()

    async def _update_loop(self) -> None:
        if self.config.offline or self.config.no_update_check or self.config.demo:
            return
        await asyncio.sleep(60)
        while True:
            with contextlib.suppress(Exception):
                await check_for_update(self.store, self.http)
            await asyncio.sleep(86400)
