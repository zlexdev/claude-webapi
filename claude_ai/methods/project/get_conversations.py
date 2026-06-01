"""GetProjectConversations: conversations attached to a project."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod
from claude_ai.models.pagination import PaginatedResponse


@dataclass(slots=True)
class GetProjectConversationsParams:
    org_uuid: str
    project_uuid: str
    limit: int = 50
    offset: int = 0


class GetProjectConversations(
    BaseMethod[GetProjectConversationsParams, PaginatedResponse]
):
    __endpoint__ = (
        "/api/organizations/{org_uuid}/projects/{project_uuid}/conversations_v2"
    )
    __http_method__ = "GET"
    __model__ = PaginatedResponse

    def build_params(self, params: GetProjectConversationsParams) -> dict[str, Any]:
        return {
            "path": {"org_uuid": params.org_uuid, "project_uuid": params.project_uuid},
            "query": {"limit": params.limit, "offset": params.offset},
        }
