"""Unit tests for the reworked event bus: registry, dispatcher, worker, stores, decorators."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from claude_ai.bus import (
    EventBusClosedError,
    EventEnvelope,
    HandlerError,
    MemoryEventBus,
    MemoryEventStore,
    NullEventStore,
    StoredEvent,
    WorkerConfig,
    WorkerStoppedError,
)
from claude_ai.bus.dispatcher import EventDispatcher
from claude_ai.bus.registry import HandlerRegistry
from claude_ai.events.base import BaseEvent
from claude_ai.middleware.base import Middleware, NextHandler
from claude_ai.middleware.manager import MiddlewareManager


class FooEvent(BaseEvent):
    type: str = "foo.created"
    payload: str = ""


class BarEvent(BaseEvent):
    type: str = "bar.created"


class TestRegistryMatching:
    async def test_class_match_with_inheritance(self) -> None:
        reg = HandlerRegistry()
        seen: list[BaseEvent] = []

        async def h(evt: BaseEvent, _data: dict[str, Any]) -> None:
            seen.append(evt)

        await reg.add(FooEvent, h)
        matched = await reg.match(FooEvent(payload="x"))
        assert len(matched) == 1
        matched = await reg.match(BarEvent())
        assert matched == []

    async def test_exact_string_match(self) -> None:
        reg = HandlerRegistry()

        async def h(_e: BaseEvent, _d: dict[str, Any]) -> None:
            pass

        await reg.add("foo.created", h)
        assert len(await reg.match(FooEvent())) == 1
        assert await reg.match(BarEvent()) == []

    async def test_glob_pattern_match(self) -> None:
        reg = HandlerRegistry()

        async def h(_e: BaseEvent, _d: dict[str, Any]) -> None:
            pass

        await reg.add("foo.*", h)
        assert len(await reg.match(FooEvent())) == 1
        assert await reg.match(BarEvent()) == []

    async def test_unsubscribe_via_subscription(self) -> None:
        reg = HandlerRegistry()

        async def h(_e: BaseEvent, _d: dict[str, Any]) -> None:
            pass

        sub = await reg.add(FooEvent, h)
        assert len(await reg.match(FooEvent())) == 1
        await sub.unsubscribe()
        assert await reg.match(FooEvent()) == []


class TestDispatcherIsolatesHandlerFailures:
    async def test_one_failing_handler_does_not_block_others(self) -> None:
        reg = HandlerRegistry()
        mw: MiddlewareManager[BaseEvent, None] = MiddlewareManager(scope="t")
        dispatcher = EventDispatcher(reg, mw)

        ok_calls: list[str] = []

        async def boom(_e: BaseEvent, _d: dict[str, Any]) -> None:
            raise RuntimeError("boom")

        async def ok(_e: BaseEvent, _d: dict[str, Any]) -> None:
            ok_calls.append("ok")

        await reg.add(FooEvent, boom, name="boom")
        await reg.add(FooEvent, ok, name="ok")

        env = EventEnvelope(event=FooEvent())
        result = await dispatcher.dispatch(env)
        assert ok_calls == ["ok"]
        assert len(result.handler_errors) == 1
        err: HandlerError = result.handler_errors[0]
        assert err.handler == "boom"
        assert err.event_type == "foo.created"
        assert isinstance(err.original, RuntimeError)
        assert "boom" in err.original_traceback

    async def test_handler_retry_attempts(self) -> None:
        reg = HandlerRegistry()
        mw: MiddlewareManager[BaseEvent, None] = MiddlewareManager(scope="t")
        dispatcher = EventDispatcher(reg, mw)
        attempts: list[int] = []

        async def flaky(_e: BaseEvent, _d: dict[str, Any]) -> None:
            attempts.append(1)
            if len(attempts) < 3:
                raise RuntimeError("not yet")

        await reg.add(FooEvent, flaky, retry_attempts=2, retry_backoff=0.001)
        result = await dispatcher.dispatch(EventEnvelope(event=FooEvent()))
        assert len(attempts) == 3
        assert result.handler_errors == []


class TestMiddlewareErrorPropagation:
    async def test_middleware_exception_recorded_not_raised(self) -> None:
        reg = HandlerRegistry()
        mw: MiddlewareManager[BaseEvent, None] = MiddlewareManager(scope="t")

        class Boom(Middleware[BaseEvent, None]):
            async def __call__(
                self,
                handler: NextHandler[BaseEvent, None],
                event: BaseEvent,
                data: dict[str, Any],
            ) -> None:
                raise ValueError("middleware boom")

        mw.use(Boom())

        async def h(_e: BaseEvent, _d: dict[str, Any]) -> None:  # never runs
            pass

        await reg.add(FooEvent, h)
        result = await EventDispatcher(reg, mw).dispatch(
            EventEnvelope(event=FooEvent())
        )
        assert result.middleware_error is not None
        assert isinstance(result.middleware_error.original, ValueError)


class TestInlineBus:
    async def test_publish_dispatches_synchronously(self) -> None:
        bus = MemoryEventBus(mode="inline")
        await bus.start()
        seen: list[BaseEvent] = []

        async def h(evt: BaseEvent, _d: dict[str, Any]) -> None:
            seen.append(evt)

        await bus.subscribe(FooEvent, h)
        await bus.publish(FooEvent(payload="hi"))
        assert len(seen) == 1
        await bus.stop()

    async def test_publish_after_close_raises(self) -> None:
        bus = MemoryEventBus(mode="inline")
        await bus.start()
        await bus.stop()
        with pytest.raises(EventBusClosedError):
            await bus.publish(FooEvent())


class TestWorkerBus:
    async def test_publish_then_flush_runs_handlers_in_background(self) -> None:
        bus = MemoryEventBus(
            mode="worker", worker_config=WorkerConfig(concurrency=2, queue_size=16)
        )
        await bus.start()
        seen: list[str] = []

        async def h(evt: BaseEvent, _d: dict[str, Any]) -> None:
            await asyncio.sleep(0.01)
            assert isinstance(evt, FooEvent)
            seen.append(evt.payload)

        await bus.subscribe(FooEvent, h)
        await bus.publish(FooEvent(payload="a"))
        await bus.publish(FooEvent(payload="b"))
        await bus.flush()
        assert sorted(seen) == ["a", "b"]
        stats = bus.stats()
        assert stats is not None
        assert stats.processed == 2
        await bus.stop()

    async def test_failing_handler_eventually_dead_letters(self) -> None:
        store = MemoryEventStore()
        bus = MemoryEventBus(
            mode="worker",
            store=store,
            worker_config=WorkerConfig(
                concurrency=1, envelope_max_attempts=2, envelope_retry_backoff=0.001
            ),
        )
        await bus.start()
        attempts = 0

        async def boom(_e: BaseEvent, _d: dict[str, Any]) -> None:
            nonlocal attempts
            attempts += 1
            raise RuntimeError("nope")

        await bus.subscribe(FooEvent, boom)
        await bus.publish(FooEvent())
        await bus.flush()
        await bus.stop()

        assert attempts == 2
        dead = await store.dead_letters()
        assert len(dead) == 1
        assert dead[0].event_type == "foo.created"
        assert "nope" in (dead[0].last_error or "")
        stats = bus.stats()
        assert stats is not None
        assert stats.dead_lettered == 1

    async def test_publish_after_stop_raises_worker_stopped(self) -> None:
        bus = MemoryEventBus(mode="worker")
        await bus.start()
        await bus.stop()
        with pytest.raises((EventBusClosedError, WorkerStoppedError)):
            await bus.publish(FooEvent())


class TestDecoratorAPI:
    async def test_on_decorator_registers_handler(self) -> None:
        bus = MemoryEventBus(mode="inline")
        await bus.start()
        seen: list[str] = []

        @bus.on(FooEvent)
        async def handle(evt: BaseEvent, _d: dict[str, Any]) -> None:
            assert isinstance(evt, FooEvent)
            seen.append(evt.payload)

        await asyncio.sleep(0)  # let the create_task in the decorator run
        await bus.publish(FooEvent(payload="via-decorator"))
        assert seen == ["via-decorator"]
        await bus.stop()

    async def test_on_decorator_with_glob(self) -> None:
        bus = MemoryEventBus(mode="inline")
        await bus.start()
        seen: list[str] = []

        @bus.on("foo.*")
        async def handle(evt: BaseEvent, _d: dict[str, Any]) -> None:
            seen.append(evt.type)

        await asyncio.sleep(0)
        await bus.publish(FooEvent())
        await bus.publish(BarEvent())
        assert seen == ["foo.created"]
        await bus.stop()


class TestMemoryStore:
    async def test_lifecycle_states(self) -> None:
        store = MemoryEventStore()
        env = EventEnvelope(event=FooEvent(payload="x"))
        await store.save(env)
        assert await store.size() == 1
        await store.mark_processed(env.id)

        replayed: list[StoredEvent] = []
        async for e in store.replay():
            replayed.append(e)
        assert replayed[0].status == "processed"

    async def test_replay_filter_by_status(self) -> None:
        store = MemoryEventStore()
        a = EventEnvelope(event=FooEvent(payload="a"))
        b = EventEnvelope(event=FooEvent(payload="b"))
        await store.save(a)
        await store.save(b)
        await store.mark_processed(a.id)
        await store.mark_failed(b.id, "err", attempt=1)

        results: list[StoredEvent] = []
        async for e in store.replay(statuses=["failed"]):
            results.append(e)
        assert len(results) == 1
        assert results[0].id == b.id


class TestNullStoreNoOp:
    async def test_save_and_replay_are_noops(self) -> None:
        store = NullEventStore()
        await store.save(EventEnvelope(event=FooEvent()))
        await store.mark_processed("anything")
        items: list[StoredEvent] = []
        async for e in store.replay():
            items.append(e)
        assert items == []
