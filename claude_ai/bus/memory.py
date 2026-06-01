"""MemoryEventBus: in-process bus.

Modes:
  'worker' (default) — `publish()` enqueues; N background tasks process via
                       middleware → handlers; failures land in `store.dead_letter()`.
  'inline'           — `publish()` runs the dispatch chain in the publisher's task.

Both modes share the same `HandlerRegistry`, `MiddlewareManager`, `EventDispatcher`,
and accept any `BaseEventStore` (Null / Memory / Redis / Mongo).
"""

from __future__ import annotations

import logging
from typing import Any, TypeVar

from claude_ai.bus.base import BaseEventBus, EventBusOptions
from claude_ai.bus.dispatcher import DispatchResult, EventDispatcher
from claude_ai.bus.envelope import EventEnvelope
from claude_ai.bus.exceptions import EventBusClosedError
from claude_ai.bus.registry import EventHandler, HandlerRegistry, Subscription
from claude_ai.bus.store.base import BaseEventStore
from claude_ai.bus.store.null import NullEventStore
from claude_ai.bus.worker import EventWorker, WorkerConfig, WorkerStats
from claude_ai.events.base import BaseEvent
from claude_ai.middleware.base import Middleware
from claude_ai.middleware.manager import MiddlewareManager

logger = logging.getLogger("claude_ai.bus")

E = TypeVar("E", bound=BaseEvent)


class MemoryEventBus(BaseEventBus):
    def __init__(
        self,
        *,
        mode: str = "worker",
        store: BaseEventStore | None = None,
        worker_config: WorkerConfig | None = None,
        options: EventBusOptions | None = None,
    ) -> None:
        if options is not None:
            mode = options.mode
            store = options.store if options.store is not None else store
            worker_config = options.worker if options.worker is not None else worker_config
        if mode not in ("worker", "inline"):
            raise ValueError(f"unknown mode {mode!r}; expected 'worker' or 'inline'")
        self._mode = mode
        self._registry = HandlerRegistry()
        self._middleware: MiddlewareManager[BaseEvent, None] = MiddlewareManager(
            scope="events"
        )
        self._dispatcher = EventDispatcher(self._registry, self._middleware)
        self._store: BaseEventStore = store or NullEventStore()
        self._worker: EventWorker | None = None
        if mode == "worker":
            self._worker = EventWorker(
                self._dispatcher, self._store, config=worker_config
            )
        self._closed = False

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def registry(self) -> HandlerRegistry:
        return self._registry

    @property
    def store(self) -> BaseEventStore:
        return self._store

    @property
    def middleware(self) -> MiddlewareManager[BaseEvent, None]:
        return self._middleware

    def use(self, middleware: Middleware[BaseEvent, None]) -> None:
        self._middleware.use(middleware)

    def stats(self) -> WorkerStats | None:
        return self._worker.stats if self._worker is not None else None

    async def start(self) -> None:
        if self._closed:
            raise EventBusClosedError("bus already closed")
        if self._worker is not None:
            await self._worker.start()
        else:
            await self._store.open()

    async def stop(self, *, graceful: bool = True) -> None:
        if self._worker is not None:
            await self._worker.stop(graceful=graceful)
        else:
            await self._store.close()
        self._closed = True

    async def flush(self) -> None:
        if self._worker is not None:
            await self._worker.flush()

    async def subscribe(
        self,
        event_type: type[E] | str,
        handler: EventHandler[E],
        *,
        retry_attempts: int = 0,
        retry_backoff: float = 0.5,
        name: str | None = None,
    ) -> Subscription[E]:
        return await self._registry.add(
            event_type,
            handler,
            retry_attempts=retry_attempts,
            retry_backoff=retry_backoff,
            name=name,
        )

    async def unsubscribe(self, subscription: Subscription[Any]) -> None:
        await subscription.unsubscribe()

    async def publish(self, event: BaseEvent) -> None:
        if self._closed:
            raise EventBusClosedError(
                "bus is closed", context={"event_type": event.type}
            )
        envelope = EventEnvelope(event=event)
        if self._worker is not None:
            await self._worker.enqueue(envelope)
            return
        await self._store.save(envelope)
        result: DispatchResult = await self._dispatcher.dispatch(envelope)
        if result.middleware_error is not None:
            await self._store.mark_failed(
                envelope.id,
                str(result.middleware_error),
                attempt=envelope.attempt,
            )
            await self._store.dead_letter(envelope, str(result.middleware_error))
            return
        if result.handler_errors:
            joined = "; ".join(str(e) for e in result.handler_errors)
            await self._store.mark_failed(envelope.id, joined, attempt=envelope.attempt)
            await self._store.dead_letter(
                envelope, joined, handler=result.handler_errors[-1].handler
            )
            return
        await self._store.mark_processed(envelope.id)
