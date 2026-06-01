"""ClaudeModel: model identifiers."""

from enum import StrEnum


class ClaudeModel(StrEnum):
    OPUS_4_6 = "claude-opus-4-6"
    SONNET_4_6 = "claude-sonnet-4-6"
    HAIKU_4_5 = "claude-haiku-4-5"
