"""ListProjects: paginated project listing for an organization."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod
from claude_ai.models.pagination import PaginatedResponse
from claude_ai.models.project import Project


@dataclass(slots=True)
class ListProjectsParams:
    org_uuid: str
    limit: int = 50
    offset: int = 0
    order_by: str = "updated_at"
    filter: str = "all"
    is_archived: bool = False
    search_query: str | None = None


class ListProjects(BaseMethod[ListProjectsParams, PaginatedResponse[Project]]):
    __endpoint__ = "/api/organizations/{org_uuid}/projects_v2"
    __http_method__ = "GET"
    __model__ = PaginatedResponse

    def build_params(self, params: ListProjectsParams) -> dict[str, Any]:
        query: dict[str, Any] = {
            "limit": params.limit,
            "offset": params.offset,
            "order_by": params.order_by,
            "filter": params.filter,
            "is_archived": params.is_archived,
        }
        if params.search_query is not None:
            query["searchQuery"] = params.search_query
        return {
            "path": {"org_uuid": params.org_uuid},
            "query": query,
        }

    def parse_response(self, data: Any) -> PaginatedResponse[Project]:
        if isinstance(data, dict) and "data" not in data:
            data = {"data": data if isinstance(data, list) else [data]}
        return PaginatedResponse[Project].model_validate(data)
