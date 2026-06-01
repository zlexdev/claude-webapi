"""Send-message request models: prompt, tools, styles, turn-uuids."""

from typing import Any

from claude_ai.models._object import ClaudeObject


class Tool(ClaudeObject):
    type: str | None = None
    name: str
    description: str | None = None


class PersonalizedStyle(ClaudeObject):
    key: str | None = None
    value: str | None = None


class TurnMessageUUIDs(ClaudeObject):
    human_message_uuid: str
    assistant_message_uuid: str


class CompletionParams(ClaudeObject):
    prompt: str
    timezone: str = "UTC"
    personalized_styles: list[PersonalizedStyle] = []
    locale: str = "en-US"
    model: str = "claude-sonnet-4-6"
    tools: list[Tool] = []
    turn_message_uuids: TurnMessageUUIDs | None = None
    attachments: list[Any] = []
    files: list[Any] = []
    sync_sources: list[Any] = []
    rendering_mode: str = "messages"
