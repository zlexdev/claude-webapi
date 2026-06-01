"""Account-lifecycle events: expiry (dead session) and parking (rate-limit cooldown)."""

from __future__ import annotations

from claude_ai.events.base import BaseEvent


class AccountExpiredEvent(BaseEvent):
    type: str = "account.expired"
    reason: str = ""


class AccountParkedEvent(BaseEvent):
    type: str = "account.parked"
    until: float | None = None
    reason: str = ""
