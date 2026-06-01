"""GetKBStats: project knowledge-base usage stats."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod
from claude_ai.models.project import KBStats


@dataclass(slots=True)
class GetKBStatsParams:
    org_uuid: str
    project_uuid: str


class GetKBStats(BaseMethod[GetKBStatsParams, KBStats]):
    __endpoint__ = "/api/organizations/{org_uuid}/projects/{project_uuid}/kb/stats"
    __http_method__ = "GET"
    __model__ = KBStats

    def build_params(self, params: GetKBStatsParams) -> dict[str, Any]:
        return {
            "path": {"org_uuid": params.org_uuid, "project_uuid": params.project_uuid},
        }
