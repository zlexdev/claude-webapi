"""StreamCollector: drains an AsyncIterator[StreamEvent] into a CompletionResult (text + thinking + metadata)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

from claude_ai.models.streaming import (
    ContentBlockDelta,
    MessageDelta,
    MessageStart,
    StreamEvent,
    TextDelta,
    ThinkingDelta,
)


@dataclass
class CompletionResult:
    text: str = ""
    thinking: str = ""
    message_id: str = ""
    message_uuid: str = ""
    parent_uuid: str = ""
    model: str = ""
    stop_reason: str | None = None
    output_tokens: int = 0
    request_id: str = ""
    trace_id: str = ""


class StreamCollector:
    def __init__(self, events: AsyncIterator[StreamEvent]) -> None:
        self._events = events

    async def collect(self) -> CompletionResult:
        result = CompletionResult()
        text_parts: list[str] = []
        thinking_parts: list[str] = []

        async for event in self._events:
            if isinstance(event, MessageStart):
                msg = event.message
                result.message_id = msg.id
                result.message_uuid = msg.uuid or ""
                result.parent_uuid = msg.parent_uuid or ""
                result.model = msg.model
                result.request_id = msg.request_id or ""
                result.trace_id = msg.trace_id or ""

            elif isinstance(event, ContentBlockDelta):
                delta = event.delta
                if isinstance(delta, TextDelta):
                    text_parts.append(delta.text)
                elif isinstance(delta, ThinkingDelta):
                    thinking_parts.append(delta.thinking)
                elif isinstance(delta, dict):
                    if delta.get("type") == "text_delta":
                        text_parts.append(delta.get("text", ""))
                    elif delta.get("type") == "thinking_delta":
                        thinking_parts.append(delta.get("thinking", ""))

            elif isinstance(event, MessageDelta):
                result.stop_reason = event.delta.stop_reason
                result.output_tokens = event.usage.output_tokens

        result.text = "".join(text_parts)
        result.thinking = "".join(thinking_parts)
        return result
