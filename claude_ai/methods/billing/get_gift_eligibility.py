"""GetGiftEligibility: whether the org may purchase a gift subscription."""

from typing import Any

from claude_ai.methods.base import RequestMethod
from claude_ai.models.billing import Eligibility


class GetGiftEligibility(RequestMethod[Eligibility]):
    __endpoint__ = "/api/billing/{org_uuid}/gift/purchase_eligibility"
    __http_method__ = "GET"
    __model__ = Eligibility

    org_uuid: str

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {"path": {"org_uuid": self.org_uuid}}
