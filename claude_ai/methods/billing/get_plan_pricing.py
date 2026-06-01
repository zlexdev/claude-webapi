"""GetPlanPricing: per-product pricing breakdown (Pro / Max 5x / Max 20x), v2."""

from typing import Any

from claude_ai.methods.base import RequestMethod
from claude_ai.models.billing import PlanPricing


class GetPlanPricing(RequestMethod[PlanPricing]):
    __endpoint__ = "/api/billing/{org_uuid}/individual_plan_pricing/v2"
    __http_method__ = "POST"
    __model__ = PlanPricing

    org_uuid: str
    country: str

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {
            "path": {"org_uuid": self.org_uuid},
            "body": {"address": {"country": self.country}},
        }
