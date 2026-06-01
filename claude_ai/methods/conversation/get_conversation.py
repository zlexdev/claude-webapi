"""GetConversation: fetch a conversation, optionally as message tree."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod
from claude_ai.models.conversation import Conversation


@dataclass(slots=True)
class GetConversationParams:
    org_uuid: str
    conv_uuid: str
    tree: bool = True
    render_all_tools: bool = True
    rendering_mode: str = "messages"
    consistency: str | None = None


class GetConversation(BaseMethod[GetConversationParams, Conversation]):
    __endpoint__ = "/api/organizations/{org_uuid}/chat_conversations/{conv_uuid}"
    __http_method__ = "GET"
    __model__ = Conversation

    def build_params(self, params: GetConversationParams) -> dict[str, Any]:
        query: dict[str, Any] = {
            "tree": params.tree,
            "render_all_tools": params.render_all_tools,
            "rendering_mode": params.rendering_mode,
        }
        if params.consistency is not None:
            query["consistency"] = params.consistency
        return {
            "path": {"org_uuid": params.org_uuid, "conv_uuid": params.conv_uuid},
            "query": query,
        }
