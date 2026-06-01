"""GetProject: single-project details."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod
from claude_ai.models.project import Project


@dataclass(slots=True)
class GetProjectParams:
    org_uuid: str
    project_uuid: str


class GetProject(BaseMethod[GetProjectParams, Project]):
    __endpoint__ = "/api/organizations/{org_uuid}/projects/{project_uuid}"
    __http_method__ = "GET"
    __model__ = Project

    def build_params(self, params: GetProjectParams) -> dict[str, Any]:
        return {
            "path": {"org_uuid": params.org_uuid, "project_uuid": params.project_uuid},
        }
