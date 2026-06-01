"""Message-lifecycle events: stream chunks, message started/complete, limit updates."""

from __future__ import annotations

from typing import Any

from claude_ai.events.base import BaseEvent
from claude_ai.models.streaming import StreamEvent


class StreamChunkEvent(BaseEvent):
    type: str = "stream.chunk"
    conv_uuid: str = ""
    event: StreamEvent | None = None


class AssistantMessageStartedEvent(BaseEvent):
    type: str = "message.started"
    conv_uuid: str = ""
    message_uuid: str = ""
    parent_uuid: str | None = None
    model: str = ""


class AssistantMessageCompleteEvent(BaseEvent):
    type: str = "message.complete"
    conv_uuid: str = ""
    message_uuid: str = ""
    text: str = ""
    thinking: str = ""
    stop_reason: str | None = None
    output_tokens: int = 0


class LimitUpdatedEvent(BaseEvent):
    type: str = "limit.updated"
    windows: dict[str, dict[str, Any]] = {}
    representative_claim: str | None = None
    overage_in_use: bool = False
