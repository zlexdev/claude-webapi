"""GetPausedSubscription: details of a paused subscription (or null)."""

from typing import Any

from claude_ai.methods.base import RequestMethod
from claude_ai.models.billing import PausedSubscription


class GetPausedSubscription(RequestMethod[PausedSubscription | None]):
    __endpoint__ = "/api/organizations/{org_uuid}/paused_subscription_details"
    __http_method__ = "GET"
    __model__ = PausedSubscription

    org_uuid: str

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {"path": {"org_uuid": self.org_uuid}}
