"""EventWorker: pool of N async tasks consuming envelopes from an asyncio queue.

Lifecycle:
  start()          -> spawn N consumer tasks
  enqueue(env)     -> backpressure-aware put (await if queue is full)
  flush()          -> wait until queue empties + all in-flight finish
  stop(graceful)   -> close intake; drain or cancel; await tasks

Failures: handler exceptions are isolated by EventDispatcher; the worker decides
whether to retry the *envelope* (with backoff) before sending it to the DLQ via
`store.dead_letter(...)`. Middleware errors fail the envelope without per-handler
retries (the chain itself is broken).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from claude_ai.bus.dispatcher import DispatchResult, EventDispatcher
from claude_ai.bus.envelope import EventEnvelope
from claude_ai.bus.exceptions import WorkerStoppedError
from claude_ai.bus.store.base import BaseEventStore

logger = logging.getLogger("claude_ai.bus.worker")


@dataclass(slots=True)
class WorkerConfig:
    concurrency: int = 4
    queue_size: int = 1024
    envelope_max_attempts: int = 3
    envelope_retry_backoff: float = 0.5
    drain_timeout: float = 30.0


@dataclass(slots=True)
class WorkerStats:
    enqueued: int = 0
    processed: int = 0
    failed: int = 0
    retried: int = 0
    dead_lettered: int = 0


class EventWorker:
    def __init__(
        self,
        dispatcher: EventDispatcher,
        store: BaseEventStore,
        *,
        config: WorkerConfig | None = None,
    ) -> None:
        self._dispatcher = dispatcher
        self._store = store
        self._config = config or WorkerConfig()
        self._queue: asyncio.Queue[EventEnvelope | None] = asyncio.Queue(
            maxsize=self._config.queue_size
        )
        self._tasks: list[asyncio.Task[None]] = []
        self._running = False
        self._stopping = False
        self._stats = WorkerStats()

    @property
    def stats(self) -> WorkerStats:
        return self._stats

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> None:
        if self._running:
            return
        await self._store.open()
        self._running = True
        self._stopping = False
        self._tasks = [
            asyncio.create_task(self._consume(), name=f"event-worker-{i}")
            for i in range(self._config.concurrency)
        ]

    async def enqueue(self, envelope: EventEnvelope) -> None:
        if not self._running or self._stopping:
            raise WorkerStoppedError(
                "cannot enqueue: worker not running",
                context={"event_type": envelope.event_type},
            )
        envelope.max_attempts = self._config.envelope_max_attempts
        await self._store.save(envelope)
        await self._queue.put(envelope)
        self._stats.enqueued += 1

    async def flush(self) -> None:
        await self._queue.join()

    async def stop(self, *, graceful: bool = True) -> None:
        if not self._running:
            return
        self._stopping = True
        if graceful:
            for _ in self._tasks:
                await self._queue.put(None)
            try:
                await asyncio.wait_for(
                    self._queue.join(), timeout=self._config.drain_timeout
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "worker drain timed out after %.1fs — cancelling consumers",
                    self._config.drain_timeout,
                )
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        self._running = False
        await self._store.close()

    async def _consume(self) -> None:
        while True:
            envelope = await self._queue.get()
            if envelope is None:
                self._queue.task_done()
                return
            try:
                await self._handle(envelope)
            except asyncio.CancelledError:
                self._queue.task_done()
                raise
            except Exception:
                logger.exception(
                    "worker consumer crashed (event=%s, id=%s)",
                    envelope.event_type,
                    envelope.id,
                )
            self._queue.task_done()

    async def _handle(self, envelope: EventEnvelope) -> None:
        result: DispatchResult = await self._dispatcher.dispatch(envelope)

        if result.middleware_error is not None:
            self._stats.failed += 1
            err = result.middleware_error
            await self._store.mark_failed(
                envelope.id, str(err), attempt=envelope.attempt
            )
            await self._store.dead_letter(envelope, str(err), handler=None)
            self._stats.dead_lettered += 1
            return

        if not result.handler_errors:
            self._stats.processed += 1
            await self._store.mark_processed(envelope.id)
            return

        if envelope.attempt < envelope.max_attempts:
            self._stats.retried += 1
            delay = self._config.envelope_retry_backoff * (2 ** (envelope.attempt - 1))
            await asyncio.sleep(delay)
            retry_env = envelope.with_attempt(
                attempt=envelope.attempt + 1,
                last_error="; ".join(str(e) for e in result.handler_errors),
            )
            await self._store.mark_failed(
                envelope.id,
                "; ".join(str(e) for e in result.handler_errors),
                attempt=envelope.attempt,
            )
            await self._queue.put(retry_env)
            return

        self._stats.failed += 1
        joined_error = "; ".join(str(e) for e in result.handler_errors)
        await self._store.mark_failed(
            envelope.id, joined_error, attempt=envelope.attempt
        )
        last_handler = result.handler_errors[-1].handler
        await self._store.dead_letter(envelope, joined_error, handler=last_handler)
        self._stats.dead_lettered += 1
