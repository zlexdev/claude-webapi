"""GenerateTitle: ask the API to title an existing conversation."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod


@dataclass(slots=True)
class GenerateTitleParams:
    org_uuid: str
    conv_uuid: str
    message_content: str = ""
    recent_titles: list[str] | None = None


class GenerateTitle(BaseMethod[GenerateTitleParams, str]):
    __endpoint__ = "/api/organizations/{org_uuid}/chat_conversations/{conv_uuid}/title"
    __http_method__ = "POST"
    __model__ = str

    def build_params(self, params: GenerateTitleParams) -> dict[str, Any]:
        return {
            "path": {"org_uuid": params.org_uuid, "conv_uuid": params.conv_uuid},
            "body": {
                "message_content": params.message_content,
                "recent_titles": params.recent_titles or [],
            },
        }

    def parse_response(self, data: Any) -> str:
        if isinstance(data, dict):
            return data.get("title", "")
        return str(data)
