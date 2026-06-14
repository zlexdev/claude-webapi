"""PromptBuilder: turn an OpenAI messages[] array into a single claude prompt.

Stateless mode flattens the whole conversation (system + role-tagged turns) into one
prompt (D8); bound mode sends only the trailing user turn (claude keeps context).
Handles both string and multimodal list ``content`` (text parts are concatenated).

Tool-call history is rendered here, in one place (F-A): an assistant turn carrying
``tool_calls`` becomes ``Assistant called: name(args)``; a ``role:"tool"`` message
becomes ``Tool result [id]: …``. There is no separate fold step — appending one on
top of ``flatten`` would double-render the results and drop the assistant's
tool-call intent (whose ``content`` is null).
"""

from __future__ import annotations

from typing import Any

from gateway.features.completion.schemas.openai import InMessage, Role, ToolCall

_ROLE_LABEL = {
    Role.SYSTEM: "System",
    Role.USER: "User",
    Role.ASSISTANT: "Assistant",
    Role.TOOL: "Tool",
}


def _text_of(content: str | list[dict[str, Any]] | None) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content:
        if block.get("type") == "text" and isinstance(block.get("text"), str):
            parts.append(block["text"])
        elif isinstance(block.get("text"), str):
            parts.append(block["text"])
    return "\n".join(parts)


def _render_tool_calls(calls: list[ToolCall]) -> str:
    return "\n".join(
        f"Assistant called: {c.function.name}({c.function.arguments})" for c in calls
    )


def has_tool_history(messages: list[InMessage]) -> bool:
    """True when the messages contain a tool round-trip (assistant call or result)."""
    return any(m.role is Role.TOOL or m.tool_calls for m in messages)


class PromptBuilder:
    @staticmethod
    def flatten(messages: list[InMessage]) -> str:
        lines: list[str] = []
        for message in messages:
            if message.role is Role.TOOL:
                ref = message.tool_call_id or message.name or ""
                body = _text_of(message.content).strip()
                lines.append(f"Tool result [{ref}]: {body}")
                continue
            if message.role is Role.ASSISTANT and message.tool_calls:
                rendered = _render_tool_calls(message.tool_calls)
                extra = _text_of(message.content).strip()
                lines.append(f"{rendered}\n{extra}".strip() if extra else rendered)
                continue
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
