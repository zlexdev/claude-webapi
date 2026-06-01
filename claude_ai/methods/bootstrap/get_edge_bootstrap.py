"""GetEdgeBootstrap: anonymous edge bootstrap (GrowthBook flags, gated messages).

`statsig_hashing_algorithm` / `growthbook_format` are fixed protocol constants;
only `include_system_prompts` is a caller knob.
"""

from typing import Any

from claude_ai.methods.base import RequestMethod


class GetEdgeBootstrap(RequestMethod[dict[str, Any]]):
    __endpoint__ = "/edge-api/bootstrap"
    __http_method__ = "GET"
    __model__ = dict

    include_system_prompts: bool = False

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {
            "query": {
                "statsig_hashing_algorithm": "djb2",
                "growthbook_format": "sdk",
                "include_system_prompts": self.include_system_prompts,
            }
        }
