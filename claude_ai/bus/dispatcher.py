"""EventDispatcher: runs middleware chain, fans out to handlers, isolates handler failures.

Pure logic — no queueing, no persistence. Reused by both inline and worker buses.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from claude_ai.bus.envelope import EventEnvelope
from claude_ai.bus.exceptions import HandlerError, MiddlewareError
from claude_ai.bus.registry import HandlerEntry, HandlerRegistry
from claude_ai.events.base import BaseEvent
from claude_ai.middleware.base import NextHandler
from claude_ai.middleware.manager import MiddlewareManager

logger = logging.getLogger("claude_ai.bus")


class DispatchResult:
    __slots__ = ("envelope", "handler_errors", "middleware_error")

    def __init__(
        self,
        envelope: EventEnvelope,
        handler_errors: list[HandlerError],
        middleware_error: MiddlewareError | None,
    ) -> None:
        self.envelope = envelope
        self.handler_errors = handler_errors
        self.middleware_error = middleware_error

    @property
    def ok(self) -> bool:
        return not self.handler_errors and self.middleware_error is None

    def __repr__(self) -> str:
        return (
            f"DispatchResult(id={self.envelope.id!r}, "
            f"ok={self.ok}, "
            f"handler_errors={len(self.handler_errors)})"
        )


class EventDispatcher:
    def __init__(
        self,
        registry: HandlerRegistry,
        middleware: MiddlewareManager[BaseEvent, None],
    ) -> None:
        self._registry = registry
        self._middleware = middleware

    async def dispatch(self, envelope: EventEnvelope) -> DispatchResult:
        envelope.mark_dispatched()
        entries = await self._registry.match(envelope.event)
        handler_errors: list[HandlerError] = []

        async def terminal(evt: BaseEvent, data: dict[str, Any]) -> None:
            if not entries:
                return
            tasks = [
                self._invoke(entry, envelope, evt, data) for entry in entries
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, HandlerError):
                    handler_errors.append(result)
                elif isinstance(result, BaseException):
                    logger.exception(
                        "Unexpected non-HandlerError raised by dispatch task: %s",
                        result,
                        exc_info=result,
                    )

        chain: NextHandler[BaseEvent, None] = self._middleware.chain(terminal).__call__
        data: dict[str, Any] = {"envelope": envelope, "trace_id": envelope.trace_id}

        middleware_error: MiddlewareError | None = None
        try:
            await chain(envelope.event, data)
        except Exception as exc:
            middleware_error = MiddlewareError(
                middleware="<chain>",
                event_type=envelope.event_type,
                envelope_id=envelope.id,
                original=exc,
            )
            logger.exception(
                "Middleware chain failed for event %s (id=%s)",
                envelope.event_type,
                envelope.id,
            )

        envelope.mark_completed()
        return DispatchResult(envelope, handler_errors, middleware_error)

    async def _invoke(
        self,
        entry: HandlerEntry,
        envelope: EventEnvelope,
        event: BaseEvent,
        data: dict[str, Any],
    ) -> HandlerError | None:
        local_data = {**data, "handler": entry.name}
        for attempt in range(1, max(entry.retry_attempts, 0) + 2):
            try:
                await entry.handler(event, local_data)
                return None
            except Exception as exc:
                if attempt > entry.retry_attempts:
                    err = HandlerError(
                        handler=entry.name,
                        event_type=envelope.event_type,
                        envelope_id=envelope.id,
                        original=exc,
                        attempt=attempt,
                    )
                    logger.error(
                        "Handler %s failed on event %s (id=%s, attempt=%d/%d): %s",
                        entry.name,
                        envelope.event_type,
                        envelope.id,
                        attempt,
                        entry.retry_attempts + 1,
                        exc,
                        exc_info=exc,
                    )
                    return err
                logger.warning(
                    "Handler %s attempt %d failed for event %s — retrying",
                    entry.name,
                    attempt,
                    envelope.event_type,
                )
                await asyncio.sleep(entry.retry_backoff * (2 ** (attempt - 1)))
        return None
