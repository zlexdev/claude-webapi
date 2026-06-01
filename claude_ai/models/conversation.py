"""Conversation and chat-message models."""

from typing import Any

from claude_ai.models._object import ClaudeObject


class ConversationSettings(ClaudeObject):
    enabled_web_search: bool | None = None
    paprika_mode: str | None = None
    enabled_monkeys_in_a_barrel: bool | None = None
    enabled_saffron: bool | None = None
    tool_search_mode: str | None = None
    preview_feature_uses_artifacts: bool | None = None
    enabled_turmeric: bool | None = None


class ChatMessage(ClaudeObject):
    uuid: str
    text: str = ""
    content: list[Any] = []
    sender: str = ""
    index: int = 0
    created_at: str | None = None
    updated_at: str | None = None
    truncated: bool = False
    attachments: list[Any] = []
    files: list[Any] = []
    sync_sources: list[Any] = []
    parent_message_uuid: str | None = None


class Conversation(ClaudeObject):
    uuid: str
    name: str = ""
    summary: str = ""
    model: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    settings: ConversationSettings = ConversationSettings()
    is_starred: bool = False
    is_temporary: bool = False
    platform: str | None = None
    current_leaf_message_uuid: str | None = None
    chat_messages: list[ChatMessage] = []
    project_uuid: str | None = None
