"""CreateConversation: create a new chat conversation in an organization."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod
from claude_ai.models.conversation import Conversation


@dataclass(slots=True)
class CreateConversationParams:
    org_uuid: str
    uuid: str
    name: str = ""
    model: str = "claude-sonnet-4-6"
    include_conversation_preferences: bool = True
    is_temporary: bool = False


class CreateConversation(BaseMethod[CreateConversationParams, Conversation]):
    __endpoint__ = "/api/organizations/{org_uuid}/chat_conversations"
    __http_method__ = "POST"
    __model__ = Conversation

    def build_params(self, params: CreateConversationParams) -> dict[str, Any]:
        return {
            "path": {"org_uuid": params.org_uuid},
            "body": {
                "uuid": params.uuid,
                "name": params.name,
                "model": params.model,
                "include_conversation_preferences": params.include_conversation_preferences,
                "is_temporary": params.is_temporary,
            },
        }
