"""EventEnvelope: wraps a BaseEvent with metadata (id, attempts, trace_id, timings).

Carried through queue → worker → middleware → handlers. Stored in event stores so
DLQ / retry logic can address a specific delivery attempt rather than the bare event.
"""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from claude_ai.events.base import BaseEvent


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class EventEnvelope:
    event: BaseEvent
    id: str = field(default_factory=lambda: _uuid.uuid4().hex)
    enqueued_at: datetime = field(default_factory=_utcnow)
    dispatched_at: datetime | None = None
    completed_at: datetime | None = None
    attempt: int = 1
    max_attempts: int = 1
    trace_id: str | None = None
    last_error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def event_type(self) -> str:
        return self.event.type

    def mark_dispatched(self) -> None:
        self.dispatched_at = _utcnow()

    def mark_completed(self) -> None:
        self.completed_at = _utcnow()

    def with_attempt(self, attempt: int, last_error: str | None) -> EventEnvelope:
        new = EventEnvelope(
            event=self.event,
            id=self.id,
            enqueued_at=self.enqueued_at,
            attempt=attempt,
            max_attempts=self.max_attempts,
            trace_id=self.trace_id,
            last_error=last_error,
            metadata=dict(self.metadata),
        )
        return new

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "event": self.event.model_dump(mode="json"),
            "enqueued_at": self.enqueued_at.isoformat(),
            "dispatched_at": (
                self.dispatched_at.isoformat() if self.dispatched_at else None
            ),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "trace_id": self.trace_id,
            "last_error": self.last_error,
            "metadata": self.metadata,
        }
