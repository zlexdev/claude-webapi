"""GetAppStart: org-scoped app-start bootstrap (GrowthBook + gated content).

Observed returning 403/404 for orgs the session can't read — the caller sees
those surfaced as errors, not silently swallowed.
"""

from typing import Any

from claude_ai.methods.base import RequestMethod


class GetAppStart(RequestMethod[dict[str, Any]]):
    __endpoint__ = "/edge-api/bootstrap/{org_uuid}/app_start"
    __http_method__ = "GET"
    __model__ = dict

    org_uuid: str
    include_system_prompts: bool = False

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {
            "path": {"org_uuid": self.org_uuid},
            "query": {
                "statsig_hashing_algorithm": "djb2",
                "growthbook_format": "sdk",
                "include_system_prompts": self.include_system_prompts,
            },
        }
