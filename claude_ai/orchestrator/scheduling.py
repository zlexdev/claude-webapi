"""AvailabilityTracker: rate-limit parking + auth quarantine for accounts.

Two ways an account becomes unavailable:
  - **parked** — a rate-limit window is exhausted; auto-released at `until` (epoch s).
  - **quarantined** — session dead (401) / manual; released only explicitly (or by a
    successful relogin hook).

`is_available()` is sync (hot path in `pick`) and lazily clears expired parks from
memory. State changes (`park` / `quarantine` / `release`) persist through a
`BaseStorage`; `load()` rebuilds on restart, dropping already-expired parks.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any

from claude_ai.events.account import AccountExpiredEvent
from claude_ai.events.message import LimitUpdatedEvent
from claude_ai.storage.kv.base import BaseStorage, StorageNamespace


class NoAvailableAccounts(RuntimeError):
    """Raised by `pick()` when clients exist but all are parked / quarantined."""

    def __init__(self, soonest_release: float | None = None) -> None:
        self.soonest_release = soonest_release
        super().__init__("no available accounts (all parked or quarantined)")


@dataclass(slots=True)
class ParkState:
    until: float | None  # epoch seconds; None = indefinite (quarantine)
    reason: str
    quarantined: bool = False


def _coerce_epoch(value: Any) -> float | None:
    try:
        secs = float(value)
    except (TypeError, ValueError):
        return None
    return secs / 1000.0 if secs > 1e12 else secs  # tolerate ms epochs


class AvailabilityTracker:
    def __init__(
        self,
        store: BaseStorage | None = None,
        *,
        park_threshold: float = 0.98,
        default_cooldown: float = 300.0,
    ) -> None:
        self._parked: dict[str, ParkState] = {}
        self._store = store
        self._threshold = park_threshold
        self._default_cooldown = default_cooldown

    async def load(self) -> None:
        if self._store is None:
            return
        now = time.time()
        raw = await self._store.items(StorageNamespace.PARKING)
        for account_id, payload in raw.items():
            state = ParkState(
                until=payload.get("until"),
                reason=payload.get("reason", ""),
                quarantined=bool(payload.get("quarantined", False)),
            )
            if state.quarantined or (state.until is not None and state.until > now):
                self._parked[account_id] = state
            else:
                await self._store.delete(StorageNamespace.PARKING, account_id)

    def is_available(self, account_id: str, now: float | None = None) -> bool:
        state = self._parked.get(account_id)
        if state is None:
            return True
        if state.quarantined or state.until is None:
            return False
        now = time.time() if now is None else now
        if now >= state.until:
            del self._parked[account_id]  # store row left to expire; load() drops it
            return True
        return False

    async def park(
        self, account_id: str, until: float | None, reason: str = ""
    ) -> None:
        now = time.time()
        if until is None or until <= now:
            until = now + self._default_cooldown
        await self._set(account_id, ParkState(until=until, reason=reason))

    async def quarantine(self, account_id: str, reason: str = "") -> None:
        await self._set(account_id, ParkState(None, reason, quarantined=True))

    async def release(self, account_id: str) -> None:
        self._parked.pop(account_id, None)
        if self._store is not None:
            await self._store.delete(StorageNamespace.PARKING, account_id)

    async def _set(self, account_id: str, state: ParkState) -> None:
        self._parked[account_id] = state
        if self._store is not None:
            await self._store.set(StorageNamespace.PARKING, account_id, asdict(state))

    def parked(self) -> dict[str, ParkState]:
        return dict(self._parked)

    def soonest_release(self, now: float | None = None) -> float | None:
        times = [
            s.until
            for s in self._parked.values()
            if s.until is not None and not s.quarantined
        ]
        return min(times) if times else None

    async def on_limit(self, event: LimitUpdatedEvent, _data: dict[str, Any]) -> None:
        windows = event.windows or {}
        h5 = windows.get("5h", {})
        d7 = windows.get("7d", {})
        account_id = event.account_id or "default"
        if float(h5.get("utilization", 0.0)) >= self._threshold:
            await self.park(account_id, _coerce_epoch(h5.get("resets_at")), "5h window exhausted")
        elif float(d7.get("utilization", 0.0)) >= self._threshold:
            await self.park(account_id, _coerce_epoch(d7.get("resets_at")), "7d window exhausted")

    async def on_expired(
        self, event: AccountExpiredEvent, _data: dict[str, Any]
    ) -> None:
        await self.quarantine(event.account_id or "default", event.reason or "session expired")
