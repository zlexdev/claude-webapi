"""BaseEventBus + EventBusOptions: ABC for inline / worker buses with decorator API.

Re-exports `Subscription` and `EventHandler` from the registry module so legacy code
that imports them from `claude_ai.bus.base` keeps working.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from claude_ai.bus.registry import EventHandler, Subscription
from claude_ai.bus.store.base import BaseEventStore
from claude_ai.bus.worker import WorkerConfig
from claude_ai.events.base import BaseEvent
from claude_ai.middleware.base import Middleware

E = TypeVar("E", bound=BaseEvent)


@dataclass(slots=True)
class EventBusOptions:
    """Knobs the bus accepts at construction.

    `mode='worker'` (default) runs handlers on a background pool — `publish()`
    returns when queued. `mode='inline'` invokes handlers in the publishing task.
    """

    mode: str = "worker"
    store: BaseEventStore | None = None
    worker: WorkerConfig | None = None


class BaseEventBus(ABC):
    @abstractmethod
    async def subscribe(
        self,
        event_type: type[E] | str,
        handler: EventHandler[E],
        *,
        retry_attempts: int = 0,
        retry_backoff: float = 0.5,
        name: str | None = None,
    ) -> Subscription[E]: ...

    def on(
        self,
        event_type: type[E] | str,
        *,
        retry_attempts: int = 0,
        retry_backoff: float = 0.5,
        name: str | None = None,
    ) -> Callable[[EventHandler[E]], EventHandler[E]]:
        """Decorator wrapper around `subscribe()`. Subscription is registered eagerly."""
        import asyncio as _asyncio

        def decorator(handler: EventHandler[E]) -> EventHandler[E]:
            coro = self.subscribe(
                event_type,
                handler,
                retry_attempts=retry_attempts,
                retry_backoff=retry_backoff,
                name=name,
            )
            try:
                loop = _asyncio.get_running_loop()
            except RuntimeError:
                _asyncio.run(coro)
            else:
                loop.create_task(coro)
            return handler

        return decorator

    @abstractmethod
    async def unsubscribe(self, subscription: Subscription[Any]) -> None: ...

    @abstractmethod
    async def publish(self, event: BaseEvent) -> None: ...

    @abstractmethod
    def use(self, middleware: Middleware[BaseEvent, None]) -> None: ...

    async def start(self) -> None:
        return None

    async def stop(self, *, graceful: bool = True) -> None:
        return None

    async def flush(self) -> None:
        return None

    async def close(self) -> None:
        await self.stop()


__all__ = [
    "BaseEventBus",
    "EventBusOptions",
    "EventHandler",
    "Subscription",
]
