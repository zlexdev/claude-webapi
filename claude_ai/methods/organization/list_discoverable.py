"""ListDiscoverable: organizations the account can join + can-create-personal flag."""

from typing import Any

from claude_ai.methods.base import RequestMethod
from claude_ai.models.settings import DiscoverableOrgs


class ListDiscoverable(RequestMethod[DiscoverableOrgs]):
    __endpoint__ = "/api/organizations/discoverable"
    __http_method__ = "GET"
    __model__ = DiscoverableOrgs

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {}
