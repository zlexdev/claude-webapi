"""ListDocs: project documents."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod
from claude_ai.models.project import ProjectDoc


@dataclass(slots=True)
class ListDocsParams:
    org_uuid: str
    project_uuid: str


class ListDocs(BaseMethod[ListDocsParams, list[ProjectDoc]]):
    __endpoint__ = "/api/organizations/{org_uuid}/projects/{project_uuid}/docs"
    __http_method__ = "GET"
    __model__ = list

    def build_params(self, params: ListDocsParams) -> dict[str, Any]:
        return {
            "path": {"org_uuid": params.org_uuid, "project_uuid": params.project_uuid},
        }

    def parse_response(self, data: Any) -> list[ProjectDoc]:
        items = data if isinstance(data, list) else []
        return [ProjectDoc.model_validate(item) for item in items]
