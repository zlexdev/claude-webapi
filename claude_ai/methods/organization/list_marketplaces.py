"""ListMarketplaces: default plugin/skill marketplaces visible to an org."""

from typing import Any

from claude_ai.methods.base import RequestMethod
from claude_ai.models.settings import MarketplaceList


class ListMarketplaces(RequestMethod[MarketplaceList]):
    __endpoint__ = "/api/organizations/{org_uuid}/marketplaces/list-default-marketplaces"
    __http_method__ = "GET"
    __model__ = MarketplaceList

    org_uuid: str

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {"path": {"org_uuid": self.org_uuid}}
