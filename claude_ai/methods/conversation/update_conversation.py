"""UpdateConversation: rename / move-to-project on a conversation."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod


@dataclass(slots=True)
class UpdateConversationParams:
    org_uuid: str
    conv_uuid: str
    name: str | None = None
    project_uuid: str | None = None


class UpdateConversation(BaseMethod[UpdateConversationParams, None]):
    __endpoint__ = "/api/organizations/{org_uuid}/chat_conversations/{conv_uuid}"
    __http_method__ = "PUT"
    __model__ = type(None)

    def build_params(self, params: UpdateConversationParams) -> dict[str, Any]:
        body = {}
        if params.name is not None:
            body["name"] = params.name
        if params.project_uuid is not None:
            body["project_uuid"] = params.project_uuid
        return {
            "path": {"org_uuid": params.org_uuid, "conv_uuid": params.conv_uuid},
            "body": body,
        }

    def parse_response(self, data: Any) -> None:
        return None
