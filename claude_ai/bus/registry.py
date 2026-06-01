"""HandlerRegistry: owns subscriptions; supports class-, exact-string-, and glob-string keys.

`@bus.on(...)` decorators delegate here. Match precedence: class hierarchy → exact string → glob → '*'.
"""

from __future__ import annotations

import asyncio
import fnmatch
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from claude_ai.events.base import BaseEvent

E = TypeVar("E", bound=BaseEvent)
EventHandler = Callable[[E, dict[str, Any]], Awaitable[None]]


@dataclass(slots=True)
class HandlerEntry:
    name: str
    handler: EventHandler[Any]
    event_type: type[BaseEvent] | str
    retry_attempts: int = 0
    retry_backoff: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)


class Subscription(Generic[E]):
    """Returned by subscribe(); call `await sub.unsubscribe()` to detach."""

    def __init__(
        self,
        entry: HandlerEntry,
        registry: HandlerRegistry,
    ) -> None:
        self._entry = entry
        self._registry = registry

    @property
    def event_type(self) -> type[BaseEvent] | str:
        return self._entry.event_type

    @property
    def handler(self) -> EventHandler[Any]:
        return self._entry.handler

    @property
    def name(self) -> str:
        return self._entry.name

    async def unsubscribe(self) -> None:
        await self._registry.remove(self._entry)


class HandlerRegistry:
    def __init__(self) -> None:
        self._by_class: dict[type[BaseEvent], list[HandlerEntry]] = {}
        self._by_exact: dict[str, list[HandlerEntry]] = {}
        self._by_glob: list[tuple[str, HandlerEntry]] = []
        self._lock = asyncio.Lock()

    @staticmethod
    def _is_glob(value: str) -> bool:
        return any(ch in value for ch in "*?[")

    @staticmethod
    def _handler_name(handler: EventHandler[Any]) -> str:
        mod = getattr(handler, "__module__", "?")
        qual = getattr(handler, "__qualname__", repr(handler))
        return f"{mod}.{qual}"

    async def add(
        self,
        event_type: type[BaseEvent] | str,
        handler: EventHandler[Any],
        *,
        retry_attempts: int = 0,
        retry_backoff: float = 0.5,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Subscription[Any]:
        entry = HandlerEntry(
            name=name or self._handler_name(handler),
            handler=handler,
            event_type=event_type,
            retry_attempts=retry_attempts,
            retry_backoff=retry_backoff,
            metadata=dict(metadata or {}),
        )
        async with self._lock:
            if isinstance(event_type, type):
                self._by_class.setdefault(event_type, []).append(entry)
            elif self._is_glob(event_type):
                self._by_glob.append((event_type, entry))
            else:
                self._by_exact.setdefault(event_type, []).append(entry)
        return Subscription(entry, self)

    async def remove(self, entry: HandlerEntry) -> None:
        async with self._lock:
            if isinstance(entry.event_type, type):
                bucket = self._by_class.get(entry.event_type, [])
                if entry in bucket:
                    bucket.remove(entry)
                return
            if isinstance(entry.event_type, str) and self._is_glob(entry.event_type):
                self._by_glob = [
                    (p, e) for p, e in self._by_glob if e is not entry
                ]
                return
            assert isinstance(entry.event_type, str)
            bucket = self._by_exact.get(entry.event_type, [])
            if entry in bucket:
                bucket.remove(entry)

    async def match(self, event: BaseEvent) -> list[HandlerEntry]:
        async with self._lock:
            entries: list[HandlerEntry] = []
            for cls, bucket in self._by_class.items():
                if isinstance(event, cls):
                    entries.extend(bucket)
            entries.extend(self._by_exact.get(event.type, []))
            for pattern, entry in self._by_glob:
                if fnmatch.fnmatchcase(event.type, pattern):
                    entries.append(entry)
            return entries

    async def all(self) -> list[HandlerEntry]:
        async with self._lock:
            out: list[HandlerEntry] = []
            for bucket in self._by_class.values():
                out.extend(bucket)
            for bucket in self._by_exact.values():
                out.extend(bucket)
            out.extend(e for _, e in self._by_glob)
            return out

    async def clear(self) -> None:
        async with self._lock:
            self._by_class.clear()
            self._by_exact.clear()
            self._by_glob.clear()
