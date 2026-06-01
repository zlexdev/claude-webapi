"""EVENT_MAP + build_event_from_payload: SSE event dispatch to typed StreamEvent subclasses."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from claude_ai.enums.stream import StreamEventType
from claude_ai.models.streaming import (
    ContentBlockDelta,
    ContentBlockStart,
    ContentBlockStop,
    MessageDelta,
    MessageLimit,
    MessageStart,
    MessageStop,
    StreamEvent,
)

logger = logging.getLogger("claude_ai")

EVENT_MAP: dict[str, type[StreamEvent]] = {
    StreamEventType.MESSAGE_START.value: MessageStart,
    StreamEventType.CONTENT_BLOCK_START.value: ContentBlockStart,
    StreamEventType.CONTENT_BLOCK_DELTA.value: ContentBlockDelta,
    StreamEventType.CONTENT_BLOCK_STOP.value: ContentBlockStop,
    StreamEventType.MESSAGE_DELTA.value: MessageDelta,
    StreamEventType.MESSAGE_STOP.value: MessageStop,
    StreamEventType.MESSAGE_LIMIT.value: MessageLimit,
}


def build_event_from_payload(event_type: str, data: dict[str, Any]) -> StreamEvent:
    cls = EVENT_MAP.get(event_type, StreamEvent)
    try:
        return cls.model_validate({**data, "type": event_type, "raw": data})
    except ValidationError as exc:
        logger.warning("Failed to parse %s event: %s", event_type, exc)
        return StreamEvent(type=event_type, raw=data)
