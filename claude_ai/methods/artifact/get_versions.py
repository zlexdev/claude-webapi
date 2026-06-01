"""GetVersions: list artifact versions for a conversation."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod
from claude_ai.models.artifact import ArtifactVersion


@dataclass(slots=True)
class GetVersionsParams:
    org_uuid: str
    conv_uuid: str
    source: str | None = None


class GetVersions(BaseMethod[GetVersionsParams, list[ArtifactVersion]]):
    __endpoint__ = "/api/organizations/{org_uuid}/artifacts/{conv_uuid}/versions"
    __http_method__ = "GET"
    __model__ = list

    def build_params(self, params: GetVersionsParams) -> dict[str, Any]:
        query: dict[str, Any] = {}
        if params.source is not None:
            query["source"] = params.source
        return {
            "path": {"org_uuid": params.org_uuid, "conv_uuid": params.conv_uuid},
            "query": query,
        }

    def parse_response(self, data: Any) -> list[ArtifactVersion]:
        raw = data.get("artifact_versions", []) if isinstance(data, dict) else []
        return [ArtifactVersion.model_validate(item) for item in raw]
