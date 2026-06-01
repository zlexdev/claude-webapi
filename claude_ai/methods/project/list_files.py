"""ListFiles: project files."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod


@dataclass(slots=True)
class ListFilesParams:
    org_uuid: str
    project_uuid: str


class ListFiles(BaseMethod[ListFilesParams, list[Any]]):
    __endpoint__ = "/api/organizations/{org_uuid}/projects/{project_uuid}/files"
    __http_method__ = "GET"
    __model__ = list

    def build_params(self, params: ListFilesParams) -> dict[str, Any]:
        return {
            "path": {"org_uuid": params.org_uuid, "project_uuid": params.project_uuid},
        }

    def parse_response(self, data: Any) -> list[Any]:
        if isinstance(data, list):
            return data
        return [data] if data else []
