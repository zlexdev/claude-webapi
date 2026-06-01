"""BaseEvent: ClaudeObject-derived event with type/account_id/occurred_at."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import Field

from claude_ai.models._object import ClaudeObject


class BaseEvent(ClaudeObject):
    type: str
    account_id: str | None = None
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
