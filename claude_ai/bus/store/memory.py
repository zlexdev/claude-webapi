"""MemoryEventStore: ordered in-memory store with separate DLQ. Useful for tests / debugging."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from claude_ai.bus.envelope import EventEnvelope
from claude_ai.bus.store.base import BaseEventStore, StoredEvent


class MemoryEventStore(BaseEventStore):
    def __init__(self) -> None:
        self._events: dict[str, StoredEvent] = {}
        self._order: list[str] = []
        self._dead: list[tuple[StoredEvent, str | None, str]] = []
        self._lock = asyncio.Lock()

    async def save(self, envelope: EventEnvelope) -> None:
        async with self._lock:
            stored = StoredEvent.from_envelope(envelope, status="pending")
            if stored.id not in self._events:
                self._order.append(stored.id)
            self._events[stored.id] = stored

    async def mark_processed(self, envelope_id: str) -> None:
        async with self._lock:
            stored = self._events.get(envelope_id)
            if stored is not None:
                stored.status = "processed"

    async def mark_failed(
        self, envelope_id: str, error: str, *, attempt: int
    ) -> None:
        async with self._lock:
            stored = self._events.get(envelope_id)
            if stored is not None:
                stored.status = "failed"
                stored.last_error = error
                stored.attempt = attempt

    async def dead_letter(
        self, envelope: EventEnvelope, error: str, *, handler: str | None = None
    ) -> None:
        async with self._lock:
            stored = StoredEvent.from_envelope(envelope, status="dead")
            stored.last_error = error
            self._dead.append((stored, handler, error))
            self._events[stored.id] = stored

    async def replay(
        self,
        *,
        event_types: list[str] | None = None,
        statuses: list[str] | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[StoredEvent]:
        async with self._lock:
            ids = list(self._order)
        emitted = 0
        for eid in ids:
            stored = self._events.get(eid)
            if stored is None:
                continue
            if event_types and stored.event_type not in event_types:
                continue
            if statuses and stored.status not in statuses:
                continue
            yield stored
            emitted += 1
            if limit is not None and emitted >= limit:
                return

    async def dead_letters(self) -> list[StoredEvent]:
        async with self._lock:
            return [stored for stored, _, _ in self._dead]

    async def size(self) -> int:
        async with self._lock:
            return len(self._events)
