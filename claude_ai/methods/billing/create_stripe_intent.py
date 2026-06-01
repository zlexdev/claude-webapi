"""CreateStripeIntent: open a Stripe SetupIntent for a chosen plan + billing address."""

from typing import Any

from claude_ai.enums.billing import BillingPlan
from claude_ai.methods.base import RequestMethod
from claude_ai.models.billing import StripeIntent


class CreateStripeIntent(RequestMethod[StripeIntent]):
    __endpoint__ = "/api/stripe/{org_uuid}/intent"
    __http_method__ = "POST"
    __model__ = StripeIntent

    org_uuid: str
    plan: BillingPlan
    country: str
    billing_address: dict[str, Any] | None = None

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {
            "path": {"org_uuid": self.org_uuid},
            "body": {
                "billingAddress": self.billing_address or {"country": self.country},
                "plan": self.plan,
                "country": self.country,
            },
        }
