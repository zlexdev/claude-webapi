"""GetRavenEligible: raven (research mode) eligibility check."""

from typing import Any

from claude_ai.methods.base import BaseMethod
from claude_ai.models.account import RavenEligibility


class GetRavenEligible(BaseMethod[None, RavenEligibility]):
    __endpoint__ = "/api/account/raven_eligible"
    __http_method__ = "GET"
    __model__ = RavenEligibility

    def build_params(self, params: None) -> dict[str, Any]:
        return {}
