"""Persist domain events (the activity log) and announce them on the bus."""

from __future__ import annotations

import time
from typing import Any

from bsmm.engine.bus import EventBus
from bsmm.models import Event, Severity
from bsmm.storage.store import Store


class EventLog:
    def __init__(self, store: Store, bus: EventBus) -> None:
        self.store = store
        self.bus = bus
        self._recent: dict[str, float] = {}

    async def emit(
        self,
        type_: str,
        title: str,
        *,
        severity: Severity = Severity.INFO,
        body: str | None = None,
        device_id: str | None = None,
        data: dict[str, Any] | None = None,
        dedupe_key: str | None = None,
        dedupe_window_s: float = 0.0,
        ts: float | None = None,
    ) -> Event | None:
        now = time.time()
        if dedupe_key and dedupe_window_s > 0:
            last = self._recent.get(dedupe_key)
            if last is not None and now - last < dedupe_window_s:
                return None
            self._recent[dedupe_key] = now
            if len(self._recent) > 2000:
                cutoff = now - 3600
                self._recent = {k: v for k, v in self._recent.items() if v > cutoff}
        ev = await self.store.add_event(
            Event(ts=ts or now, type=type_, severity=severity, device_id=device_id, title=title, body=body,
                  data=data or {}, dedupe_key=dedupe_key)
        )
        self.bus.publish("event", ev.model_dump(mode="json"))
        return ev
