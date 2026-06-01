"""AddDoc: attach a text document to a project."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod
from claude_ai.models.project import ProjectDoc


@dataclass(slots=True)
class AddDocParams:
    org_uuid: str
    project_uuid: str
    file_name: str
    content: str


class AddDoc(BaseMethod[AddDocParams, ProjectDoc]):
    __endpoint__ = "/api/organizations/{org_uuid}/projects/{project_uuid}/docs"
    __http_method__ = "POST"
    __model__ = ProjectDoc

    def build_params(self, params: AddDocParams) -> dict[str, Any]:
        return {
            "path": {"org_uuid": params.org_uuid, "project_uuid": params.project_uuid},
            "body": {"file_name": params.file_name, "content": params.content},
        }
