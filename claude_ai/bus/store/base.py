"""BaseEventStore: persistence contract for envelopes + dead-letter records.

Used by `EventWorker` to durably record published events and any handler/middleware
failures. Implementations: Null, Memory, Redis, Mongo.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from claude_ai.bus.envelope import EventEnvelope


@dataclass(slots=True)
class StoredEvent:
    id: str
    event_type: str
    payload: dict[str, Any]
    enqueued_at: datetime
    attempt: int
    status: str = "pending"
    last_error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_envelope(cls, env: EventEnvelope, status: str = "pending") -> StoredEvent:
        return cls(
            id=env.id,
            event_type=env.event_type,
            payload=env.event.model_dump(mode="json"),
            enqueued_at=env.enqueued_at,
            attempt=env.attempt,
            status=status,
            last_error=env.last_error,
            metadata=dict(env.metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "payload": self.payload,
            "enqueued_at": self.enqueued_at.isoformat(),
            "attempt": self.attempt,
            "status": self.status,
            "last_error": self.last_error,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoredEvent:
        ts = data.get("enqueued_at")
        if isinstance(ts, str):
            enqueued_at = datetime.fromisoformat(ts)
        elif isinstance(ts, datetime):
            enqueued_at = ts
        else:
            enqueued_at = datetime.now(timezone.utc)
        return cls(
            id=data["id"],
            event_type=data["event_type"],
            payload=data.get("payload", {}),
            enqueued_at=enqueued_at,
            attempt=data.get("attempt", 1),
            status=data.get("status", "pending"),
            last_error=data.get("last_error"),
            metadata=data.get("metadata", {}),
        )


class BaseEventStore(ABC):
    @abstractmethod
    async def save(self, envelope: EventEnvelope) -> None: ...

    @abstractmethod
    async def mark_processed(self, envelope_id: str) -> None: ...

    @abstractmethod
    async def mark_failed(
        self, envelope_id: str, error: str, *, attempt: int
    ) -> None: ...

    @abstractmethod
    async def dead_letter(
        self, envelope: EventEnvelope, error: str, *, handler: str | None = None
    ) -> None: ...

    @abstractmethod
    async def replay(
        self,
        *,
        event_types: list[str] | None = None,
        statuses: list[str] | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[StoredEvent]: ...

    async def open(self) -> None:
        return None

    async def close(self) -> None:
        return None
