"""ListConversations: paginated list of conversations (org-scoped)."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod
from claude_ai.models.conversation import Conversation
from claude_ai.models.pagination import PaginatedResponse


@dataclass(slots=True)
class ListConversationsParams:
    org_uuid: str
    limit: int = 50
    starred: bool | None = None
    consistency: str | None = None


class ListConversations(
    BaseMethod[ListConversationsParams, PaginatedResponse[Conversation]]
):
    __endpoint__ = "/api/organizations/{org_uuid}/chat_conversations_v2"
    __http_method__ = "GET"
    __model__ = PaginatedResponse

    def build_params(self, params: ListConversationsParams) -> dict[str, Any]:
        query: dict[str, Any] = {"limit": params.limit}
        if params.starred is not None:
            query["starred"] = params.starred
        if params.consistency is not None:
            query["consistency"] = params.consistency
        return {
            "path": {"org_uuid": params.org_uuid},
            "query": query,
        }

    def parse_response(self, data: Any) -> PaginatedResponse[Conversation]:
        if isinstance(data, dict) and "data" not in data:
            data = {"data": data if isinstance(data, list) else [data]}
        return PaginatedResponse[Conversation].model_validate(data)
