"""Domain exceptions for the event bus. All chain via `from` so original tracebacks survive."""

from __future__ import annotations

import traceback
from typing import Any


class EventBusError(Exception):
    """Root for every bus-related failure."""

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, Any] = context or {}

    def __str__(self) -> str:
        if not self.context:
            return self.message
        ctx = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
        return f"{self.message} [{ctx}]"


class EventBusClosedError(EventBusError):
    """Bus operation attempted after close()."""


class WorkerStoppedError(EventBusError):
    """publish() called while worker is stopping or stopped."""


class EventValidationError(EventBusError):
    """Replayed/restored payload could not be validated into BaseEvent."""


class EventStoreError(EventBusError):
    """Persistent store I/O failure (connect, read, write)."""


class HandlerError(EventBusError):
    """Handler raised — wraps with handler name + envelope id; original is `__cause__`."""

    def __init__(
        self,
        handler: str,
        event_type: str,
        envelope_id: str,
        original: BaseException,
        *,
        attempt: int = 1,
    ) -> None:
        super().__init__(
            f"handler {handler!r} failed on event {event_type!r}",
            context={
                "handler": handler,
                "event_type": event_type,
                "envelope_id": envelope_id,
                "attempt": attempt,
                "original": f"{type(original).__name__}: {original}",
            },
        )
        self.handler = handler
        self.event_type = event_type
        self.envelope_id = envelope_id
        self.attempt = attempt
        self.original = original
        self.original_traceback = "".join(
            traceback.format_exception(type(original), original, original.__traceback__)
        )


class MiddlewareError(EventBusError):
    """Middleware raised before reaching the handler. Original is `__cause__`."""

    def __init__(
        self,
        middleware: str,
        event_type: str,
        envelope_id: str,
        original: BaseException,
    ) -> None:
        super().__init__(
            f"middleware {middleware!r} failed on event {event_type!r}",
            context={
                "middleware": middleware,
                "event_type": event_type,
                "envelope_id": envelope_id,
                "original": f"{type(original).__name__}: {original}",
            },
        )
        self.middleware = middleware
        self.event_type = event_type
        self.envelope_id = envelope_id
        self.original = original
