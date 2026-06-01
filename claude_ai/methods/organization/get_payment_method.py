"""GetPaymentMethod: the org's stored card (or null when none on file)."""

from typing import Any

from claude_ai.methods.base import RequestMethod
from claude_ai.models.organization import PaymentMethod


class GetPaymentMethod(RequestMethod[PaymentMethod | None]):
    __endpoint__ = "/api/organizations/{org_uuid}/payment_method"
    __http_method__ = "GET"
    __model__ = PaymentMethod

    org_uuid: str

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {"path": {"org_uuid": self.org_uuid}}
