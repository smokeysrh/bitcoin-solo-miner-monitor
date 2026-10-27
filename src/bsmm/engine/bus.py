"""A tiny in-process publish/subscribe bus (feeds the live stream, the alert engine and the UI)."""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class BusMessage:
    topic: str
    data: dict[str, Any]
    seq: int
    ts: float = field(default_factory=time.time)


class Subscription:
    def __init__(self, bus: EventBus, topics: set[str] | None, maxsize: int) -> None:
        self._bus = bus
        self.topics = topics
        self.queue: asyncio.Queue[BusMessage | None] = asyncio.Queue(maxsize=maxsize)
        self.dropped = 0
        self._closed = False

    def matches(self, topic: str) -> bool:
        return self.topics is None or topic in self.topics

    def put(self, msg: BusMessage) -> None:
        if self._closed:
            return
        if self.queue.full():  # a slow consumer loses its oldest message, never blocks the engine
            try:
                self.queue.get_nowait()
                self.dropped += 1
            except asyncio.QueueEmpty:
                pass
        self.queue.put_nowait(msg)

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._bus._subs.discard(self)
            with contextlib.suppress(asyncio.QueueFull):
                self.queue.put_nowait(None)

    async def __aiter__(self) -> AsyncIterator[BusMessage]:
        while True:
            msg = await self.queue.get()
            if msg is None:
                return
            yield msg

    async def get(self, timeout: float | None = None) -> BusMessage | None:
        try:
            return await asyncio.wait_for(self.queue.get(), timeout)
        except TimeoutError:
            return None


class EventBus:
    def __init__(self) -> None:
        self._subs: set[Subscription] = set()
        self._seq = 0

    def publish(self, topic: str, data: dict[str, Any]) -> BusMessage:
        self._seq += 1
        msg = BusMessage(topic=topic, data=data, seq=self._seq)
        for sub in list(self._subs):
            if sub.matches(topic):
                sub.put(msg)
        return msg

    def subscribe(self, topics: set[str] | list[str] | None = None, maxsize: int = 512) -> Subscription:
        sub = Subscription(self, set(topics) if topics else None, maxsize)
        self._subs.add(sub)
        return sub

    @property
    def subscriber_count(self) -> int:
        return len(self._subs)

    def close_all(self) -> None:
        for sub in list(self._subs):
            sub.close()
