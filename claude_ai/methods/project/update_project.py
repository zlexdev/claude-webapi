"""UpdateProject: rename / re-describe a project."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod


@dataclass(slots=True)
class UpdateProjectParams:
    org_uuid: str
    project_uuid: str
    name: str | None = None
    description: str | None = None
    is_private: bool | None = None


class UpdateProject(BaseMethod[UpdateProjectParams, None]):
    __endpoint__ = "/api/organizations/{org_uuid}/projects/{project_uuid}"
    __http_method__ = "PUT"
    __model__ = type(None)

    def build_params(self, params: UpdateProjectParams) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if params.name is not None:
            body["name"] = params.name
        if params.description is not None:
            body["description"] = params.description
        if params.is_private is not None:
            body["is_private"] = params.is_private
        return {
            "path": {"org_uuid": params.org_uuid, "project_uuid": params.project_uuid},
            "body": body or None,
        }

    def parse_response(self, data: Any) -> None:
        return None
