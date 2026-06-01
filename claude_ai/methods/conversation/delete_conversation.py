"""DeleteConversation: delete a single conversation."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod


@dataclass(slots=True)
class DeleteConversationParams:
    org_uuid: str
    conv_uuid: str


class DeleteConversation(BaseMethod[DeleteConversationParams, None]):
    __endpoint__ = "/api/organizations/{org_uuid}/chat_conversations/{conv_uuid}"
    __http_method__ = "DELETE"
    __model__ = type(None)

    def build_params(self, params: DeleteConversationParams) -> dict[str, Any]:
        return {
            "path": {"org_uuid": params.org_uuid, "conv_uuid": params.conv_uuid},
        }

    def parse_response(self, data: Any) -> None:
        return None
