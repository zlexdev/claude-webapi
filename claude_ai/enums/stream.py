"""SSE-related enums: StreamEventType, ContentBlockType, DeltaType, StopReason, LimitStatus, LimitWindow, RoleType, MessageType."""

from enum import StrEnum


class StreamEventType(StrEnum):
    MESSAGE_START = "message_start"
    CONTENT_BLOCK_START = "content_block_start"
    CONTENT_BLOCK_DELTA = "content_block_delta"
    CONTENT_BLOCK_STOP = "content_block_stop"
    MESSAGE_DELTA = "message_delta"
    MESSAGE_STOP = "message_stop"
    MESSAGE_LIMIT = "message_limit"


class ContentBlockType(StrEnum):
    TEXT = "text"
    THINKING = "thinking"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"


class DeltaType(StrEnum):
    TEXT = "text_delta"
    THINKING = "thinking_delta"
    THINKING_SUMMARY = "thinking_summary_delta"
    TOOL_USE_BLOCK_UPDATE = "tool_use_block_update_delta"
    INPUT_JSON = "input_json_delta"
    CITATION_START = "citation_start_delta"
    CITATION_END = "citation_end_delta"


class StopReason(StrEnum):
    END_TURN = "end_turn"
    MAX_TOKENS = "max_tokens"
    STOP_SEQUENCE = "stop_sequence"
    TOOL_USE = "tool_use"
    REFUSAL = "refusal"


class LimitStatus(StrEnum):
    WITHIN_LIMIT = "within_limit"
    APPROACHING = "approaching_limit"
    EXCEEDED = "exceeded_limit"


class LimitWindow(StrEnum):
    H5 = "5h"
    D7 = "7d"


class RoleType(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageType(StrEnum):
    MESSAGE = "message"
