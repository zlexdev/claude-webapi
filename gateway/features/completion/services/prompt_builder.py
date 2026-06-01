"""PromptBuilder: turn an OpenAI messages[] array into a single claude prompt.

Stateless mode flattens the whole conversation (system + role-tagged turns) into one
prompt (D8); bound mode sends only the trailing user turn (claude keeps context).
Handles both string and multimodal list ``content`` (text parts are concatenated).
"""

from __future__ import annotations

from typing import Any

from gateway.features.completion.schemas.openai import InMessage, Role

_ROLE_LABEL = {
    Role.SYSTEM: "System",
    Role.USER: "User",
    Role.ASSISTANT: "Assistant",
    Role.TOOL: "Tool",
}


def _text_of(content: str | list[dict[str, Any]]) -> str:
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content:
        if block.get("type") == "text" and isinstance(block.get("text"), str):
            parts.append(block["text"])
        elif isinstance(block.get("text"), str):
            parts.append(block["text"])
    return "\n".join(parts)


class PromptBuilder:
    @staticmethod
    def flatten(messages: list[InMessage]) -> str:
        lines: list[str] = []
        for message in messages:
            label = _ROLE_LABEL.get(message.role, message.role.value.title())
            text = _text_of(message.content).strip()
            if text:
                lines.append(f"{label}: {text}")
        return "\n\n".join(lines)

    @staticmethod
    def last_user(messages: list[InMessage]) -> str:
        for message in reversed(messages):
            if message.role is Role.USER:
                text = _text_of(message.content).strip()
                if text:
                    return text
        # no user turn — fall back to the flattened conversation
        return PromptBuilder.flatten(messages)
