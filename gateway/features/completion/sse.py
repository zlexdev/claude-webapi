"""Map SDK stream events / CompletionResult to the OpenAI wire shapes + SSE framing."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from claude_ai.models.streaming import ContentBlockDelta, MessageDelta, TextDelta
from gateway.features.completion.schemas.openai import (
    ChatChoice,
    ChatCompletionChunk,
    ChatCompletionResponse,
    ChunkChoice,
    OutMessage,
    Usage,
)

DONE = "data: [DONE]\n\n"

_FINISH = {"end_turn": "stop", "stop_sequence": "stop", "max_tokens": "length"}


def completion_id() -> str:
    return f"chatcmpl-{uuid.uuid4().hex}"


def now_epoch() -> int:
    return int(datetime.now(UTC).timestamp())


def map_finish(stop_reason: str | None) -> str | None:
    if stop_reason is None:
        return None
    return _FINISH.get(stop_reason, "stop")


def text_of_event(event: Any) -> str | None:
    if isinstance(event, ContentBlockDelta):
        delta = event.delta
        if isinstance(delta, TextDelta):
            return delta.text  # type: ignore[no-any-return]  # SDK TextDelta untyped
        if isinstance(delta, dict) and delta.get("type") == "text_delta":
            text = delta.get("text", "")
            return text if isinstance(text, str) else None
    return None


def finish_of_event(event: Any) -> str | None:
    if isinstance(event, MessageDelta):
        return map_finish(event.delta.stop_reason)
    return None


def make_chunk(
    *, id_: str, created: int, model: str, delta: dict[str, Any], finish_reason: str | None = None
) -> ChatCompletionChunk:
    return ChatCompletionChunk(
        id=id_,
        created=created,
        model=model,
        choices=[ChunkChoice(delta=delta, finish_reason=finish_reason)],
    )


def sse_line(chunk: ChatCompletionChunk) -> str:
    return f"data: {chunk.model_dump_json()}\n\n"


def estimate_tokens(text: str) -> int:
    return max(0, len(text) // 4)


def make_response(
    *, text: str, stop_reason: str | None, output_tokens: int, model: str, prompt: str
) -> ChatCompletionResponse:
    prompt_tokens = estimate_tokens(prompt)
    return ChatCompletionResponse(
        id=completion_id(),
        created=now_epoch(),
        model=model,
        choices=[
            ChatChoice(
                message=OutMessage(content=text),
                finish_reason=map_finish(stop_reason) or "stop",
            )
        ],
        usage=Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=output_tokens,
            total_tokens=prompt_tokens + output_tokens,
        ),
    )
