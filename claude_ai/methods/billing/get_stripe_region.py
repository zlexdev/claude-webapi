"""GetStripeRegion: resolve the Stripe account region for a country + org."""

from typing import Any

from claude_ai.methods.base import RequestMethod
from claude_ai.models.billing import StripeRegion


class GetStripeRegion(RequestMethod[StripeRegion]):
    __endpoint__ = "/api/billing/stripe_region"
    __http_method__ = "GET"
    __model__ = StripeRegion

    country: str
    organization_uuid: str

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {
            "query": {
                "country": self.country,
                "organization_uuid": self.organization_uuid,
            }
        }
