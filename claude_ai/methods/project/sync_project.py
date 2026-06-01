"""SyncProject: trigger external-source sync for a project."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod


@dataclass(slots=True)
class SyncProjectParams:
    org_uuid: str
    project_uuid: str


class SyncProject(BaseMethod[SyncProjectParams, None]):
    __endpoint__ = "/api/organizations/{org_uuid}/projects/{project_uuid}/sync"
    __http_method__ = "POST"
    __model__ = type(None)

    def build_params(self, params: SyncProjectParams) -> dict[str, Any]:
        return {
            "path": {"org_uuid": params.org_uuid, "project_uuid": params.project_uuid},
        }

    def parse_response(self, data: Any) -> None:
        return None
