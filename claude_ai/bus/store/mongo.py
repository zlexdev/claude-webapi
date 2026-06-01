"""MongoEventStore: MongoDB-backed persistence using two collections (events + dead_letters).

Requires `motor>=3` (async MongoDB driver). Lazy imported — no hard dep.

Collections (configurable):
  events         { _id, event_type, payload, enqueued_at, attempt, status, last_error, metadata }
  dead_letters   { event_id, event_type, payload, error, handler, ts, attempt }
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from claude_ai.bus.envelope import EventEnvelope
from claude_ai.bus.exceptions import EventStoreError
from claude_ai.bus.store.base import BaseEventStore, StoredEvent


class MongoEventStore(BaseEventStore):
    def __init__(
        self,
        url: str = "mongodb://localhost:27017",
        *,
        database: str = "claude_ai",
        events_collection: str = "events",
        dead_collection: str = "dead_letters",
        client: Any = None,
    ) -> None:
        self._url = url
        self._db_name = database
        self._events_name = events_collection
        self._dead_name = dead_collection
        self._owned = client is None
        self._client: Any = client
        self._db: Any = None
        self._events: Any = None
        self._dead: Any = None

    async def open(self) -> None:
        if self._events is not None:
            return
        if self._client is None:
            try:
                from motor.motor_asyncio import AsyncIOMotorClient
            except ImportError as exc:
                raise EventStoreError(
                    "motor package required for MongoEventStore (pip install motor)"
                ) from exc
            try:
                self._client = AsyncIOMotorClient(self._url)
            except Exception as exc:
                raise EventStoreError(
                    "failed to connect to Mongo", context={"url": self._url}
                ) from exc
        self._db = self._client[self._db_name]
        self._events = self._db[self._events_name]
        self._dead = self._db[self._dead_name]
        try:
            await self._events.create_index("enqueued_at")
            await self._events.create_index("event_type")
            await self._events.create_index("status")
        except Exception:
            pass

    async def close(self) -> None:
        if self._client is None or not self._owned:
            return
        self._client.close()
        self._client = None
        self._events = None
        self._dead = None

    async def _ensure(self) -> None:
        if self._events is None:
            await self.open()

    async def save(self, envelope: EventEnvelope) -> None:
        await self._ensure()
        stored = StoredEvent.from_envelope(envelope, status="pending")
        doc = stored.to_dict()
        doc["_id"] = doc.pop("id")
        doc["enqueued_at"] = envelope.enqueued_at
        try:
            await self._events.replace_one({"_id": stored.id}, doc, upsert=True)
        except Exception as exc:
            raise EventStoreError(
                "mongo save failed", context={"id": stored.id}
            ) from exc

    async def mark_processed(self, envelope_id: str) -> None:
        await self._ensure()
        try:
            await self._events.update_one(
                {"_id": envelope_id}, {"$set": {"status": "processed"}}
            )
        except Exception as exc:
            raise EventStoreError(
                "mongo mark_processed failed", context={"id": envelope_id}
            ) from exc

    async def mark_failed(
        self, envelope_id: str, error: str, *, attempt: int
    ) -> None:
        await self._ensure()
        try:
            await self._events.update_one(
                {"_id": envelope_id},
                {
                    "$set": {
                        "status": "failed",
                        "last_error": error,
                        "attempt": attempt,
                    }
                },
            )
        except Exception as exc:
            raise EventStoreError(
                "mongo mark_failed failed", context={"id": envelope_id}
            ) from exc

    async def dead_letter(
        self, envelope: EventEnvelope, error: str, *, handler: str | None = None
    ) -> None:
        await self._ensure()
        try:
            await self._dead.insert_one(
                {
                    "event_id": envelope.id,
                    "event_type": envelope.event_type,
                    "payload": envelope.event.model_dump(mode="json"),
                    "error": error,
                    "handler": handler,
                    "ts": datetime.now(timezone.utc),
                    "attempt": envelope.attempt,
                }
            )
            await self._events.update_one(
                {"_id": envelope.id},
                {"$set": {"status": "dead", "last_error": error}},
            )
        except Exception as exc:
            raise EventStoreError(
                "mongo dead_letter failed", context={"id": envelope.id}
            ) from exc

    async def replay(
        self,
        *,
        event_types: list[str] | None = None,
        statuses: list[str] | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[StoredEvent]:
        await self._ensure()
        query: dict[str, Any] = {}
        if event_types:
            query["event_type"] = {"$in": event_types}
        if statuses:
            query["status"] = {"$in": statuses}
        cursor = self._events.find(query).sort("enqueued_at", 1)
        if limit is not None:
            cursor = cursor.limit(limit)
        try:
            async for doc in cursor:
                doc = dict(doc)
                doc["id"] = doc.pop("_id")
                yield StoredEvent.from_dict(doc)
        except Exception as exc:
            raise EventStoreError("mongo replay failed") from exc
