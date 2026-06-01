"""Bus handlers used by ClaudeOrchestrator.

Each tracker is a plain class with one or more `async def on_*` coroutines that
match the EventHandler signature `(event, data) -> None`. The orchestrator wires
them on its bus during `start()`. None of them touch claude.ai directly — they only
maintain in-memory state derived from events emitted by HttpSession / HttpxTransport.

Trackers:
  - LimitTracker         account_id → LimitState (drives bus-backed selector)
  - MessageMetrics       per-account counters: started/completed/tokens/by_model
  - ProxyBlacklist       invalid proxy URLs with last reason + count
  - StreamRecorder       (opt-in) buffers last N stream chunks per conversation,
                         useful for debugging / replay.
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from claude_ai.events.message import (
    AssistantMessageCompleteEvent,
    AssistantMessageStartedEvent,
    LimitUpdatedEvent,
    StreamChunkEvent,
)
from claude_ai.events.proxy import ProxyInvalidEvent

logger = logging.getLogger("claude_ai.orchestrator")


@dataclass(slots=True)
class LimitSnapshot:
    utilization_5h: float = 0.0
    utilization_7d: float = 0.0
    resets_5h_at: int | None = None
    resets_7d_at: int | None = None
    representative_claim: str | None = None
    overage_in_use: bool = False
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def score(self) -> float:
        return max(self.utilization_5h, self.utilization_7d)


class LimitTracker:
    """Maintains a per-account `LimitSnapshot` driven by `LimitUpdatedEvent`."""

    def __init__(self) -> None:
        self._by_account: dict[str, LimitSnapshot] = {}

    def get(self, account_id: str) -> LimitSnapshot:
        return self._by_account.get(account_id, LimitSnapshot())

    def all(self) -> dict[str, LimitSnapshot]:
        return dict(self._by_account)

    async def on_event(
        self, event: LimitUpdatedEvent, _data: dict[str, Any]
    ) -> None:
        account_id = event.account_id or "default"
        windows = event.windows or {}
        h5 = windows.get("5h", {})
        d7 = windows.get("7d", {})
        snap = LimitSnapshot(
            utilization_5h=float(h5.get("utilization", 0.0)),
            utilization_7d=float(d7.get("utilization", 0.0)),
            resets_5h_at=h5.get("resets_at"),
            resets_7d_at=d7.get("resets_at"),
            representative_claim=event.representative_claim,
            overage_in_use=event.overage_in_use,
        )
        self._by_account[account_id] = snap
        logger.debug(
            "limit updated: account=%s 5h=%.2f 7d=%.2f overage=%s",
            account_id,
            snap.utilization_5h,
            snap.utilization_7d,
            snap.overage_in_use,
        )


@dataclass(slots=True)
class AccountMetrics:
    started: int = 0
    completed: int = 0
    failed: int = 0
    output_tokens: int = 0
    by_model: dict[str, int] = field(default_factory=dict)
    last_completed_at: datetime | None = None


class MessageMetrics:
    """Per-account counters for assistant messages.

    `in_flight()` returns started - completed (useful as bulkhead signal).
    """

    def __init__(self) -> None:
        self._by_account: dict[str, AccountMetrics] = defaultdict(AccountMetrics)

    def get(self, account_id: str) -> AccountMetrics:
        return self._by_account.get(account_id, AccountMetrics())

    def in_flight(self, account_id: str) -> int:
        m = self._by_account.get(account_id)
        if m is None:
            return 0
        return max(m.started - m.completed - m.failed, 0)

    def all(self) -> dict[str, AccountMetrics]:
        return dict(self._by_account)

    async def on_started(
        self, event: AssistantMessageStartedEvent, _data: dict[str, Any]
    ) -> None:
        m = self._by_account[event.account_id or "default"]
        m.started += 1
        if event.model:
            m.by_model[event.model] = m.by_model.get(event.model, 0) + 1

    async def on_complete(
        self, event: AssistantMessageCompleteEvent, _data: dict[str, Any]
    ) -> None:
        m = self._by_account[event.account_id or "default"]
        m.completed += 1
        m.output_tokens += int(event.output_tokens or 0)
        m.last_completed_at = datetime.now(timezone.utc)


@dataclass(slots=True)
class ProxyRecord:
    url: str
    reason: str
    fail_count: int = 1
    first_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ProxyBlacklist:
    """Records proxies that failed at least once. Caller decides eviction policy."""

    def __init__(self) -> None:
        self._records: dict[str, ProxyRecord] = {}

    def is_blacklisted(self, url: str) -> bool:
        return url in self._records

    def all(self) -> dict[str, ProxyRecord]:
        return dict(self._records)

    def clear(self) -> None:
        self._records.clear()

    async def on_invalid(
        self, event: ProxyInvalidEvent, _data: dict[str, Any]
    ) -> None:
        if not event.proxy_url:
            return
        rec = self._records.get(event.proxy_url)
        if rec is None:
            self._records[event.proxy_url] = ProxyRecord(
                url=event.proxy_url, reason=event.reason
            )
            return
        rec.fail_count += 1
        rec.reason = event.reason or rec.reason
        rec.last_seen_at = datetime.now(timezone.utc)


class StreamRecorder:
    """Ring-buffer of recent SSE chunks per conversation. Off by default in orchestrator."""

    def __init__(self, max_chunks_per_conv: int = 200) -> None:
        self._max = max_chunks_per_conv
        self._buffers: dict[str, deque[Any]] = defaultdict(
            lambda: deque(maxlen=self._max)
        )

    def chunks(self, conv_uuid: str) -> list[Any]:
        return list(self._buffers.get(conv_uuid, ()))

    def clear(self, conv_uuid: str | None = None) -> None:
        if conv_uuid is None:
            self._buffers.clear()
        else:
            self._buffers.pop(conv_uuid, None)

    async def on_chunk(
        self, event: StreamChunkEvent, _data: dict[str, Any]
    ) -> None:
        self._buffers[event.conv_uuid].append(event.event)
