"""GetPermissions: per-user permission view for a project."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod
from claude_ai.models.project import ProjectPermissions


@dataclass(slots=True)
class GetPermissionsParams:
    org_uuid: str
    project_uuid: str


class GetPermissions(BaseMethod[GetPermissionsParams, ProjectPermissions]):
    __endpoint__ = "/api/organizations/{org_uuid}/projects/{project_uuid}/permissions"
    __http_method__ = "GET"
    __model__ = ProjectPermissions

    def build_params(self, params: GetPermissionsParams) -> dict[str, Any]:
        return {
            "path": {"org_uuid": params.org_uuid, "project_uuid": params.project_uuid},
        }
