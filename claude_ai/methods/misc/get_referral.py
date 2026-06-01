"""GetReferral: the account's referral program state (or null when ineligible)."""

from typing import Any

from claude_ai.methods.base import RequestMethod


class GetReferral(RequestMethod[dict[str, Any] | None]):
    __endpoint__ = "/api/referral"
    __http_method__ = "GET"
    __model__ = dict

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {}
