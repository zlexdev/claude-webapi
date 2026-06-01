"""Unit tests for orchestrator bus integration: trackers, metrics, selectors."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable
from typing import Any
from unittest.mock import MagicMock

import pytest

from claude_ai import (
    AssistantMessageCompleteEvent,
    AssistantMessageStartedEvent,
    BusBackedLeastUtilizationSelector,
    ClaudeOrchestrator,
    LeastInFlightSelector,
    LimitTracker,
    LimitUpdatedEvent,
    MemoryEventBus,
    MessageMetrics,
    ProxyBlacklist,
    ProxyInvalidEvent,
    StreamChunkEvent,
    StreamRecorder,
)
from claude_ai.client import ClaudeAIClient
from claude_ai.orchestrator.selector import BaseClientSelector


def _make_fake_client(account_id: str) -> ClaudeAIClient:
    """Cheap stand-in: orchestrator only touches `.account_id`, `.bus`, `.cache`,
    and async open()/close(). Avoid real HttpSession to keep tests offline."""
    client = MagicMock(spec=ClaudeAIClient)
    client.account_id = account_id
    client.bus = None
    client.cache = None

    async def _aopen() -> None:
        return None

    async def _aclose() -> None:
        return None

    client.open.side_effect = _aopen
    client.close.side_effect = _aclose
    return client


class TestLimitTracker:
    async def test_records_per_account_utilization(self) -> None:
        tracker = LimitTracker()
        await tracker.on_event(
            LimitUpdatedEvent(
                account_id="acc1",
                windows={
                    "5h": {"utilization": 0.4, "resets_at": 1234},
                    "7d": {"utilization": 0.8, "resets_at": 9999},
                },
                representative_claim="five_hour",
                overage_in_use=False,
            ),
            {},
        )
        snap = tracker.get("acc1")
        assert snap.utilization_5h == pytest.approx(0.4)
        assert snap.utilization_7d == pytest.approx(0.8)
        assert snap.score() == pytest.approx(0.8)
        assert tracker.get("unknown").score() == 0.0


class TestMessageMetrics:
    async def test_in_flight_counts_started_minus_completed(self) -> None:
        metrics = MessageMetrics()
        await metrics.on_started(
            AssistantMessageStartedEvent(
                account_id="acc", conv_uuid="c", message_uuid="m1", model="opus"
            ),
            {},
        )
        await metrics.on_started(
            AssistantMessageStartedEvent(
                account_id="acc", conv_uuid="c", message_uuid="m2", model="opus"
            ),
            {},
        )
        assert metrics.in_flight("acc") == 2
        await metrics.on_complete(
            AssistantMessageCompleteEvent(
                account_id="acc",
                conv_uuid="c",
                message_uuid="m1",
                output_tokens=12,
            ),
            {},
        )
        assert metrics.in_flight("acc") == 1
        m = metrics.get("acc")
        assert m.started == 2 and m.completed == 1
        assert m.output_tokens == 12
        assert m.by_model == {"opus": 2}


class TestProxyBlacklist:
    async def test_records_and_increments_failures(self) -> None:
        bl = ProxyBlacklist()
        await bl.on_invalid(
            ProxyInvalidEvent(proxy_url="http://p1", reason="ConnectError"), {}
        )
        await bl.on_invalid(
            ProxyInvalidEvent(proxy_url="http://p1", reason="ConnectError"), {}
        )
        await bl.on_invalid(
            ProxyInvalidEvent(proxy_url="http://p2", reason="TLS"), {}
        )
        assert bl.is_blacklisted("http://p1")
        assert bl.all()["http://p1"].fail_count == 2
        assert bl.all()["http://p2"].fail_count == 1

    async def test_empty_url_ignored(self) -> None:
        bl = ProxyBlacklist()
        await bl.on_invalid(ProxyInvalidEvent(proxy_url="", reason="x"), {})
        assert not bl.all()


class TestStreamRecorder:
    async def test_buffers_per_conv_with_cap(self) -> None:
        rec = StreamRecorder(max_chunks_per_conv=2)
        for i in range(3):
            await rec.on_chunk(
                StreamChunkEvent(conv_uuid="c1", event=None), {}
            )
        assert len(rec.chunks("c1")) == 2


class TestSelectors:
    async def test_bus_backed_selector_picks_lowest(self) -> None:
        tracker = LimitTracker()
        await tracker.on_event(
            LimitUpdatedEvent(
                account_id="hi",
                windows={"5h": {"utilization": 0.95}, "7d": {"utilization": 0.5}},
            ),
            {},
        )
        await tracker.on_event(
            LimitUpdatedEvent(
                account_id="lo",
                windows={"5h": {"utilization": 0.1}, "7d": {"utilization": 0.2}},
            ),
            {},
        )
        sel = BusBackedLeastUtilizationSelector(tracker)
        chosen = await sel.pick(
            [_make_fake_client("hi"), _make_fake_client("lo")]
        )
        assert chosen.account_id == "lo"

    async def test_least_in_flight_selector(self) -> None:
        metrics = MessageMetrics()
        for _ in range(3):
            await metrics.on_started(
                AssistantMessageStartedEvent(
                    account_id="busy", conv_uuid="c", message_uuid="m"
                ),
                {},
            )
        await metrics.on_started(
            AssistantMessageStartedEvent(
                account_id="quiet", conv_uuid="c", message_uuid="m"
            ),
            {},
        )
        sel = LeastInFlightSelector(metrics)
        chosen = await sel.pick(
            [_make_fake_client("busy"), _make_fake_client("quiet")]
        )
        assert chosen.account_id == "quiet"


class _StubSelector(BaseClientSelector):
    async def pick(self, clients: Iterable[ClaudeAIClient]) -> ClaudeAIClient:
        candidates = list(clients)
        return candidates[0]


class TestOrchestratorHandlerWiring:
    async def test_start_registers_all_handlers_and_routes_events(self) -> None:
        bus = MemoryEventBus(mode="inline")
        orch = ClaudeOrchestrator(bus=bus, selector=_StubSelector())
        await orch.start()
        try:
            await bus.publish(
                LimitUpdatedEvent(
                    account_id="a",
                    windows={"5h": {"utilization": 0.3}, "7d": {"utilization": 0.5}},
                )
            )
            await bus.publish(
                AssistantMessageStartedEvent(
                    account_id="a", conv_uuid="c", message_uuid="m1", model="opus"
                )
            )
            await bus.publish(
                AssistantMessageCompleteEvent(
                    account_id="a",
                    conv_uuid="c",
                    message_uuid="m1",
                    output_tokens=42,
                )
            )
            await bus.publish(ProxyInvalidEvent(proxy_url="http://p", reason="x"))
            await bus.flush()

            assert orch.limits.get("a").score() == pytest.approx(0.5)
            assert orch.metrics.get("a").started == 1
            assert orch.metrics.get("a").completed == 1
            assert orch.metrics.get("a").output_tokens == 42
            assert orch.proxies.is_blacklisted("http://p")
        finally:
            await orch.close()

    async def test_close_unsubscribes_handlers(self) -> None:
        bus = MemoryEventBus(mode="inline")
        orch = ClaudeOrchestrator(bus=bus, selector=_StubSelector())
        await orch.start()
        await orch.close()
        # bus is closed; publishing should raise
        from claude_ai.bus import EventBusClosedError, WorkerStoppedError

        with pytest.raises((EventBusClosedError, WorkerStoppedError)):
            await bus.publish(LimitUpdatedEvent(account_id="x"))

    async def test_record_stream_buffers_chunks(self) -> None:
        bus = MemoryEventBus(mode="inline")
        orch = ClaudeOrchestrator(
            bus=bus, selector=_StubSelector(), record_stream=True
        )
        await orch.start()
        try:
            await bus.publish(StreamChunkEvent(conv_uuid="c1", event=None))
            await bus.publish(StreamChunkEvent(conv_uuid="c1", event=None))
            await bus.flush()
            assert orch.stream_recorder is not None
            assert len(orch.stream_recorder.chunks("c1")) == 2
        finally:
            await orch.close()

    async def test_default_selector_is_bus_backed(self) -> None:
        orch = ClaudeOrchestrator()
        await orch.start()
        try:
            assert isinstance(
                orch.selector, BusBackedLeastUtilizationSelector
            )
        finally:
            await orch.close()
