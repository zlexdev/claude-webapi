"""Client selectors.

LeastUtilizationSelector — score = min over clients of max(5h, 7d) util.
RoundRobinSelector       — cycle index.
BusBackedLeastUtilization — same as LeastUtilization but reads from a `LimitTracker`
                            populated by `LimitUpdatedEvent`s on the bus, so the
                            picker doesn't need to reach into client.session.
LeastInFlight            — score = number of in-flight assistant messages from
                           `MessageMetrics`. Drives bulkhead-style routing.
"""

from __future__ import annotations

import itertools
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from claude_ai.client import ClaudeAIClient
    from claude_ai.orchestrator.handlers import LimitTracker, MessageMetrics


class BaseClientSelector(ABC):
    @abstractmethod
    async def pick(self, clients: Iterable[ClaudeAIClient]) -> ClaudeAIClient: ...


class LeastUtilizationSelector(BaseClientSelector):
    async def pick(self, clients: Iterable[ClaudeAIClient]) -> ClaudeAIClient:
        candidates = list(clients)
        if not candidates:
            raise RuntimeError("No clients registered in orchestrator")
        return min(candidates, key=_score)


def _score(client: ClaudeAIClient) -> float:
    state = getattr(client.session, "limit_state", None)
    return state.score() if state is not None else 0.0


class RoundRobinSelector(BaseClientSelector):
    def __init__(self) -> None:
        self._counter = itertools.count()

    async def pick(self, clients: Iterable[ClaudeAIClient]) -> ClaudeAIClient:
        candidates = list(clients)
        if not candidates:
            raise RuntimeError("No clients registered in orchestrator")
        idx = next(self._counter) % len(candidates)
        return candidates[idx]


class BusBackedLeastUtilizationSelector(BaseClientSelector):
    def __init__(self, tracker: LimitTracker) -> None:
        self._tracker = tracker

    async def pick(self, clients: Iterable[ClaudeAIClient]) -> ClaudeAIClient:
        candidates = list(clients)
        if not candidates:
            raise RuntimeError("No clients registered in orchestrator")
        return min(candidates, key=lambda c: self._tracker.get(c.account_id).score())


class LeastInFlightSelector(BaseClientSelector):
    def __init__(self, metrics: MessageMetrics) -> None:
        self._metrics = metrics

    async def pick(self, clients: Iterable[ClaudeAIClient]) -> ClaudeAIClient:
        candidates = list(clients)
        if not candidates:
            raise RuntimeError("No clients registered in orchestrator")
        return min(candidates, key=lambda c: self._metrics.in_flight(c.account_id))
