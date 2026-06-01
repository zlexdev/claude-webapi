"""GetConsumerPricing: localized price + tax for the consumer (Pro) plan."""

from typing import Any

from claude_ai.enums.status import BillingInterval
from claude_ai.methods.base import RequestMethod
from claude_ai.models.billing import ConsumerPricing


class GetConsumerPricing(RequestMethod[ConsumerPricing]):
    __endpoint__ = "/api/billing/{org_uuid}/consumer_pricing"
    __http_method__ = "POST"
    __model__ = ConsumerPricing

    org_uuid: str
    country: str
    billing_interval: BillingInterval = BillingInterval.MONTHLY

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {
            "path": {"org_uuid": self.org_uuid},
            "body": {"country": self.country, "billingInterval": self.billing_interval},
        }
