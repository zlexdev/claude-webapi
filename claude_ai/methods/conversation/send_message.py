"""SendMessage: streaming completion endpoint (SSE)."""

from dataclasses import dataclass, field
from typing import Any

from claude_ai.methods.base import BaseMethod


@dataclass(slots=True)
class SendMessageParams:
    org_uuid: str
    conv_uuid: str
    prompt: str
    model: str = "claude-sonnet-4-6"
    timezone: str = "UTC"
    locale: str = "en-US"
    rendering_mode: str = "messages"
    attachments: list[Any] = field(default_factory=list)
    files: list[Any] = field(default_factory=list)
    sync_sources: list[Any] = field(default_factory=list)
    personalized_styles: list[Any] = field(default_factory=list)
    tools: list[Any] = field(default_factory=list)
    human_message_uuid: str = ""
    assistant_message_uuid: str = ""

    def __post_init__(self) -> None:
        has_human = bool(self.human_message_uuid)
        has_assistant = bool(self.assistant_message_uuid)
        if has_human != has_assistant:
            raise ValueError(
                "Both human_message_uuid and assistant_message_uuid must be set or both empty"
            )


class SendMessage(BaseMethod[SendMessageParams, dict]):
    __endpoint__ = (
        "/api/organizations/{org_uuid}/chat_conversations/{conv_uuid}/completion"
    )
    __http_method__ = "POST"
    __model__ = dict
    __is_stream__ = True

    def build_params(self, params: SendMessageParams) -> dict[str, Any]:
        body: dict[str, Any] = {
            "prompt": params.prompt,
            "model": params.model,
            "timezone": params.timezone,
            "locale": params.locale,
            "rendering_mode": params.rendering_mode,
            "attachments": params.attachments,
            "files": params.files,
            "sync_sources": params.sync_sources,
            "personalized_styles": params.personalized_styles,
            "tools": params.tools,
        }
        if params.human_message_uuid and params.assistant_message_uuid:
            body["turn_message_uuids"] = {
                "human_message_uuid": params.human_message_uuid,
                "assistant_message_uuid": params.assistant_message_uuid,
            }
        return {
            "path": {"org_uuid": params.org_uuid, "conv_uuid": params.conv_uuid},
            "body": body,
            "headers": {
                "referer": f"https://claude.ai/chat/{params.conv_uuid}",
            },
        }
