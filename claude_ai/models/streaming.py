"""SSE stream event models: MessageStart, ContentBlock*, deltas, MessageDelta/Limit/Stop, LimitWindowState."""

from typing import Any, Literal

from claude_ai.enums.stream import (
    ContentBlockType,
    DeltaType,
    LimitStatus,
    StreamEventType,
)
from claude_ai.models._object import ClaudeObject


class StreamEvent(ClaudeObject):
    type: str
    raw: dict[str, Any] = {}


class MessageStartData(ClaudeObject):
    id: str = ""
    type: str = "message"
    role: str = "assistant"
    model: str = ""
    parent_uuid: str | None = None
    uuid: str | None = None
    content: list[Any] = []
    stop_reason: str | None = None
    trace_id: str | None = None
    request_id: str | None = None


class MessageStart(StreamEvent):
    type: Literal[StreamEventType.MESSAGE_START] = StreamEventType.MESSAGE_START
    message: MessageStartData = MessageStartData()
    discarded_parent_message_uuid: str | None = None


class ContentBlock(ClaudeObject):
    type: ContentBlockType | str = ""
    start_timestamp: str | None = None
    stop_timestamp: str | None = None
    flags: dict[str, Any] | None = None
    text: str | None = None
    citations: list[Any] | None = None
    thinking: str | None = None
    summaries: list[dict[str, Any]] | None = None
    cut_off: bool | None = None
    truncated: bool | None = None
    alternative_display_type: str | None = None
    id: str | None = None
    name: str | None = None
    input: dict[str, Any] | None = None
    tool_use_id: str | None = None
    content: Any = None


class ContentBlockStart(StreamEvent):
    type: Literal[StreamEventType.CONTENT_BLOCK_START] = (
        StreamEventType.CONTENT_BLOCK_START
    )
    index: int = 0
    content_block: ContentBlock = ContentBlock()


class TextDelta(ClaudeObject):
    type: Literal[DeltaType.TEXT] = DeltaType.TEXT
    text: str = ""


class ThinkingDelta(ClaudeObject):
    type: Literal[DeltaType.THINKING] = DeltaType.THINKING
    thinking: str = ""


class ThinkingSummary(ClaudeObject):
    summary: str = ""


class ThinkingSummaryDelta(ClaudeObject):
    type: Literal[DeltaType.THINKING_SUMMARY] = DeltaType.THINKING_SUMMARY
    summary: ThinkingSummary = ThinkingSummary()


class InputJsonDelta(ClaudeObject):
    type: Literal[DeltaType.INPUT_JSON] = DeltaType.INPUT_JSON
    partial_json: str = ""


class ToolUseBlockUpdate(ClaudeObject):
    type: Literal[DeltaType.TOOL_USE_BLOCK_UPDATE] = DeltaType.TOOL_USE_BLOCK_UPDATE
    input: dict[str, Any] | None = None
    name: str | None = None


class CitationStartDelta(ClaudeObject):
    type: Literal[DeltaType.CITATION_START] = DeltaType.CITATION_START
    citation: dict[str, Any] = {}


class CitationEndDelta(ClaudeObject):
    type: Literal[DeltaType.CITATION_END] = DeltaType.CITATION_END


BlockDelta = (
    TextDelta
    | ThinkingDelta
    | ThinkingSummaryDelta
    | InputJsonDelta
    | ToolUseBlockUpdate
    | CitationStartDelta
    | CitationEndDelta
)


class ContentBlockDelta(StreamEvent):
    type: Literal[StreamEventType.CONTENT_BLOCK_DELTA] = (
        StreamEventType.CONTENT_BLOCK_DELTA
    )
    index: int = 0
    delta: BlockDelta | dict[str, Any] = {}


class ContentBlockStop(StreamEvent):
    type: Literal[StreamEventType.CONTENT_BLOCK_STOP] = (
        StreamEventType.CONTENT_BLOCK_STOP
    )
    index: int = 0
    stop_timestamp: str | None = None


class UsageInfo(ClaudeObject):
    output_tokens: int = 0


class StopDelta(ClaudeObject):
    stop_reason: str | None = None
    stop_sequence: str | None = None


class MessageDelta(StreamEvent):
    type: Literal[StreamEventType.MESSAGE_DELTA] = StreamEventType.MESSAGE_DELTA
    delta: StopDelta = StopDelta()
    usage: UsageInfo = UsageInfo()


class MessageStop(StreamEvent):
    type: Literal[StreamEventType.MESSAGE_STOP] = StreamEventType.MESSAGE_STOP


class LimitWindowState(ClaudeObject):
    status: LimitStatus | str = LimitStatus.WITHIN_LIMIT
    resets_at: int | None = None
    utilization: float = 0.0


class MessageLimitInfo(ClaudeObject):
    type: LimitStatus | str = LimitStatus.WITHIN_LIMIT
    resetsAt: int | None = None
    remaining: int | None = None
    perModelLimit: int | None = None
    representativeClaim: str | None = None
    overageDisabledReason: str | None = None
    overageInUse: bool = False
    windows: dict[str, LimitWindowState] = {}


class MessageLimit(StreamEvent):
    type: Literal[StreamEventType.MESSAGE_LIMIT] = StreamEventType.MESSAGE_LIMIT
    message_limit: MessageLimitInfo = MessageLimitInfo()
