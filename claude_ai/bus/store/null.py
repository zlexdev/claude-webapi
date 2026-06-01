"""NullEventStore: zero-overhead store. Default when persistence isn't configured."""

from __future__ import annotations

from collections.abc import AsyncIterator

from claude_ai.bus.envelope import EventEnvelope
from claude_ai.bus.store.base import BaseEventStore, StoredEvent


class NullEventStore(BaseEventStore):
    async def save(self, envelope: EventEnvelope) -> None:
        return None

    async def mark_processed(self, envelope_id: str) -> None:
        return None

    async def mark_failed(
        self, envelope_id: str, error: str, *, attempt: int
    ) -> None:
        return None

    async def dead_letter(
        self, envelope: EventEnvelope, error: str, *, handler: str | None = None
    ) -> None:
        return None

    async def replay(
        self,
        *,
        event_types: list[str] | None = None,
        statuses: list[str] | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[StoredEvent]:
        if False:  # pragma: no cover
            yield StoredEvent(
                id="", event_type="", payload={}, enqueued_at=None, attempt=0  # type: ignore[arg-type]
            )
