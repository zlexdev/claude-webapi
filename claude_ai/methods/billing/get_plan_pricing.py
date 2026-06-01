"""GetPlanPricing: per-product pricing breakdown (Pro / Max 5x / Max 20x), v2.

Response is a deeply-nested per-product / per-period price matrix that mutates
with promos and proration — returned raw as ``dict`` rather than over-modeled.
"""

from typing import Any

from claude_ai.methods.base import RequestMethod


class GetPlanPricing(RequestMethod[dict[str, Any]]):
    __endpoint__ = "/api/billing/{org_uuid}/individual_plan_pricing/v2"
    __http_method__ = "POST"
    __model__ = dict

    org_uuid: str
    country: str

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {
            "path": {"org_uuid": self.org_uuid},
            "body": {"address": {"country": self.country}},
        }
