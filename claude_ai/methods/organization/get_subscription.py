"""GetSubscription: subscription plan and entitlements."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod
from claude_ai.models.organization import SubscriptionDetails


@dataclass(slots=True)
class GetSubscriptionParams:
    org_uuid: str


class GetSubscription(BaseMethod[GetSubscriptionParams, SubscriptionDetails]):
    __endpoint__ = "/api/organizations/{org_uuid}/subscription_details"
    __http_method__ = "GET"
    __model__ = SubscriptionDetails

    def build_params(self, params: GetSubscriptionParams) -> dict[str, Any]:
        return {
            "path": {"org_uuid": params.org_uuid},
        }
