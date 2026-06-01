"""Event bus: pub/sub with middleware, background worker, decorators, and persistent stores."""

from claude_ai.bus.base import (
    BaseEventBus,
    EventBusOptions,
    EventHandler,
    Subscription,
)
from claude_ai.bus.dispatcher import DispatchResult, EventDispatcher
from claude_ai.bus.envelope import EventEnvelope
from claude_ai.bus.exceptions import (
    EventBusClosedError,
    EventBusError,
    EventStoreError,
    EventValidationError,
    HandlerError,
    MiddlewareError,
    WorkerStoppedError,
)
from claude_ai.bus.memory import MemoryEventBus
from claude_ai.bus.registry import HandlerEntry, HandlerRegistry
from claude_ai.bus.store import (
    BaseEventStore,
    MemoryEventStore,
    NullEventStore,
    StoredEvent,
)
from claude_ai.bus.worker import EventWorker, WorkerConfig, WorkerStats

__all__ = [
    "BaseEventBus",
    "BaseEventStore",
    "DispatchResult",
    "EventBusClosedError",
    "EventBusError",
    "EventBusOptions",
    "EventDispatcher",
    "EventEnvelope",
    "EventHandler",
    "EventStoreError",
    "EventValidationError",
    "EventWorker",
    "HandlerEntry",
    "HandlerError",
    "HandlerRegistry",
    "MemoryEventBus",
    "MemoryEventStore",
    "MiddlewareError",
    "NullEventStore",
    "StoredEvent",
    "Subscription",
    "WorkerConfig",
    "WorkerStats",
    "WorkerStoppedError",
]
