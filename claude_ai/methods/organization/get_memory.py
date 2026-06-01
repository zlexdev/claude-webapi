"""GetMemory: org/project memory store."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod
from claude_ai.models.organization import Memory


@dataclass(slots=True)
class GetMemoryParams:
    org_uuid: str
    project_uuid: str | None = None


class GetMemory(BaseMethod[GetMemoryParams, Memory]):
    __endpoint__ = "/api/organizations/{org_uuid}/memory"
    __http_method__ = "GET"
    __model__ = Memory

    def build_params(self, params: GetMemoryParams) -> dict[str, Any]:
        query: dict[str, Any] = {}
        if params.project_uuid is not None:
            query["project_uuid"] = params.project_uuid
        return {
            "path": {"org_uuid": params.org_uuid},
            "query": query,
        }
