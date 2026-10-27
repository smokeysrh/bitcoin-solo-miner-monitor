"""Fan a notification out to the user's channels, honouring severity filters and quiet hours."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from datetime import time as dtime
from typing import Any

import httpx

from bsmm.engine.events import EventLog
from bsmm.models import Channel, Severity
from bsmm.notify.channels import CHANNEL_CLASSES, ChannelError, Notification
from bsmm.settings import SettingsService
from bsmm.storage.store import Store

log = logging.getLogger(__name__)
ALWAYS_LOUD = {"block_found"}


@dataclass(slots=True)
class DeliveryResult:
    channel_id: str
    name: str
    kind: str
    ok: bool
    error: str | None = None
    skipped: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {f: getattr(self, f) for f in self.__slots__}


def _parse_hhmm(text: str) -> dtime | None:
    try:
        h, m = text.split(":")
        return dtime(int(h), int(m))
    except (ValueError, AttributeError):
        return None


def in_quiet_hours(quiet: dict[str, Any] | None, now: datetime | None = None) -> bool:
    if not quiet:
        return False
    start, end = _parse_hhmm(quiet.get("start", "")), _parse_hhmm(quiet.get("end", ""))
    if not start or not end:
        return False
    t = (now or datetime.now()).time()
    if start <= end:
        return start <= t < end
    return t >= start or t < end  # overnight window


class Notifier:
    def __init__(self, store: Store, settings: SettingsService, http: httpx.AsyncClient, events: EventLog | None = None) -> None:
        self.store = store
        self.settings = settings
        self.http = http
        self.events = events

    async def _deliver(self, ch: Channel, n: Notification, secret: dict[str, str] | None = None) -> DeliveryResult:
        cls = CHANNEL_CLASSES.get(ch.kind)
        if cls is None:
            return DeliveryResult(ch.id, ch.name, ch.kind, False, error=f"unknown channel type {ch.kind!r}")
        secret = secret if secret is not None else await self.store.channel_secret(ch.id)
        impl = cls(ch.config, secret, self.http)
        last: str | None = None
        for attempt in range(2):
            try:
                await impl.send(n)
                return DeliveryResult(ch.id, ch.name, ch.kind, True)
            except ChannelError as e:
                last = str(e)
                if attempt == 0 and ("did not answer" in last or "could not connect" in last or "HTTP 5" in last):
                    await asyncio.sleep(2)
                    continue
                break
            except Exception as e:
                log.exception("channel %s crashed", ch.name)
                last = f"{e.__class__.__name__}"
                break
        return DeliveryResult(ch.id, ch.name, ch.kind, False, error=last)

    async def dispatch(self, n: Notification, channel_ids: list[str] | None = None) -> list[DeliveryResult]:
        channels = [c for c in await self.store.list_channels() if c.enabled]
        if channel_ids:
            channels = [c for c in channels if c.id in channel_ids]
        muted = (
            n.severity.rank < Severity.WARNING.rank
            and n.type not in ALWAYS_LOUD
            and in_quiet_hours(self.settings.current.alerts.quiet_hours)
        )
        results: list[DeliveryResult] = []
        jobs = []
        for ch in channels:
            if n.severity.rank < ch.min_severity.rank and n.type not in ALWAYS_LOUD:
                results.append(DeliveryResult(ch.id, ch.name, ch.kind, True, skipped=f"below this channel's minimum ({ch.min_severity.value})"))
            elif muted:
                results.append(DeliveryResult(ch.id, ch.name, ch.kind, True, skipped="quiet hours"))
            else:
                jobs.append(self._deliver(ch, n))
        results.extend(await asyncio.gather(*jobs))
        for r in results:
            if not r.ok and self.events:
                await self.events.emit(
                    "notification_failed", f"Could not send to {r.name}", severity=Severity.WARNING, body=r.error,
                    dedupe_key=f"notify-fail:{r.channel_id}", dedupe_window_s=3600, data={"channel_id": r.channel_id},
                )
        return results

    async def send_test(self, channel_id: str) -> DeliveryResult:
        ch = await self.store.get_channel(channel_id)
        if ch is None:
            raise KeyError(channel_id)
        n = Notification(title="Test notification", body="If you can read this, alerts will reach you here.", severity=Severity.SUCCESS, type="test")
        return await self._deliver(ch, n)

    async def send_test_inline(self, kind: str, config: dict[str, Any], secret: dict[str, str]) -> DeliveryResult:
        ch = Channel(id="inline", kind=kind, name="Test", config=config)
        n = Notification(title="Test notification", body="If you can read this, alerts will reach you here.", severity=Severity.SUCCESS, type="test")
        return await self._deliver(ch, n, secret=secret)
