"""GetOverageSpendLimit: configured prepaid-overage spend cap for an org (or null)."""

from typing import Any

from claude_ai.methods.base import RequestMethod


class GetOverageSpendLimit(RequestMethod[dict[str, Any] | None]):
    __endpoint__ = "/api/organizations/{org_uuid}/overage_spend_limit"
    __http_method__ = "GET"
    __model__ = dict

    org_uuid: str

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {"path": {"org_uuid": self.org_uuid}}
