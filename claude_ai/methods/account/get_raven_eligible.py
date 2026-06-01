"""GetRavenEligible: raven (research mode) eligibility check."""

from typing import Any

from claude_ai.methods.base import BaseMethod


class GetRavenEligible(BaseMethod[None, dict[str, Any]]):
    __endpoint__ = "/api/account/raven_eligible"
    __http_method__ = "GET"
    __model__ = dict

    def build_params(self, params: None) -> dict[str, Any]:
        return {}

    def parse_response(self, data: Any) -> dict[str, Any]:
        return data
