"""RedisEventStore: Redis-backed persistence using a hash for events + a list for DLQ.

Layout (configurable via key_prefix, default 'claude_ai:events'):
  HASH  {prefix}:items   field=envelope_id  value=JSON(StoredEvent)
  LIST  {prefix}:order   ids in publish order (RPUSH)
  LIST  {prefix}:dead    JSON(StoredEvent + handler/error) (RPUSH)

Requires `redis>=5.0` (uses `redis.asyncio`). Lazy imported — no hard dep.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from claude_ai.bus.envelope import EventEnvelope
from claude_ai.bus.exceptions import EventStoreError
from claude_ai.bus.store.base import BaseEventStore, StoredEvent


class RedisEventStore(BaseEventStore):
    def __init__(
        self,
        url: str = "redis://localhost:6379/0",
        *,
        key_prefix: str = "claude_ai:events",
        client: Any = None,
    ) -> None:
        self._url = url
        self._prefix = key_prefix.rstrip(":")
        self._owned = client is None
        self._client: Any = client

    @property
    def _items_key(self) -> str:
        return f"{self._prefix}:items"

    @property
    def _order_key(self) -> str:
        return f"{self._prefix}:order"

    @property
    def _dead_key(self) -> str:
        return f"{self._prefix}:dead"

    async def open(self) -> None:
        if self._client is not None:
            return
        try:
            from redis.asyncio import from_url
        except ImportError as exc:
            raise EventStoreError(
                "redis package required for RedisEventStore (pip install redis)"
            ) from exc
        try:
            self._client = from_url(self._url, decode_responses=True)
            await self._client.ping()
        except Exception as exc:
            raise EventStoreError(
                "failed to connect to Redis", context={"url": self._url}
            ) from exc

    async def close(self) -> None:
        if self._client is None or not self._owned:
            return
        try:
            await self._client.aclose()
        except Exception:
            pass
        self._client = None

    async def _get_client(self) -> Any:
        if self._client is None:
            await self.open()
        return self._client

    async def save(self, envelope: EventEnvelope) -> None:
        client = await self._get_client()
        stored = StoredEvent.from_envelope(envelope, status="pending")
        try:
            pipe = client.pipeline()
            pipe.hset(self._items_key, stored.id, json.dumps(stored.to_dict()))
            pipe.rpush(self._order_key, stored.id)
            await pipe.execute()
        except Exception as exc:
            raise EventStoreError(
                "redis save failed", context={"id": stored.id}
            ) from exc

    async def _update(
        self, envelope_id: str, **changes: Any
    ) -> None:
        client = await self._get_client()
        try:
            raw = await client.hget(self._items_key, envelope_id)
            if raw is None:
                return
            data = json.loads(raw)
            data.update(changes)
            await client.hset(self._items_key, envelope_id, json.dumps(data))
        except Exception as exc:
            raise EventStoreError(
                "redis update failed", context={"id": envelope_id}
            ) from exc

    async def mark_processed(self, envelope_id: str) -> None:
        await self._update(envelope_id, status="processed")

    async def mark_failed(
        self, envelope_id: str, error: str, *, attempt: int
    ) -> None:
        await self._update(
            envelope_id, status="failed", last_error=error, attempt=attempt
        )

    async def dead_letter(
        self, envelope: EventEnvelope, error: str, *, handler: str | None = None
    ) -> None:
        client = await self._get_client()
        stored = StoredEvent.from_envelope(envelope, status="dead")
        stored.last_error = error
        record = {**stored.to_dict(), "handler": handler}
        try:
            pipe = client.pipeline()
            pipe.hset(self._items_key, stored.id, json.dumps(stored.to_dict()))
            pipe.rpush(self._dead_key, json.dumps(record))
            await pipe.execute()
        except Exception as exc:
            raise EventStoreError(
                "redis dead_letter failed", context={"id": stored.id}
            ) from exc

    async def replay(
        self,
        *,
        event_types: list[str] | None = None,
        statuses: list[str] | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[StoredEvent]:
        client = await self._get_client()
        try:
            ids = await client.lrange(self._order_key, 0, -1)
        except Exception as exc:
            raise EventStoreError("redis replay failed") from exc
        emitted = 0
        for eid in ids:
            raw = await client.hget(self._items_key, eid)
            if raw is None:
                continue
            stored = StoredEvent.from_dict(json.loads(raw))
            if event_types and stored.event_type not in event_types:
                continue
            if statuses and stored.status not in statuses:
                continue
            yield stored
            emitted += 1
            if limit is not None and emitted >= limit:
                return
