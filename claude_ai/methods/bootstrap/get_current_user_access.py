"""GetCurrentUserAccess: account + org feature flags and permissions."""

from typing import Any

from claude_ai.methods.base import RequestMethod
from claude_ai.models.bootstrap import CurrentUserAccess


class GetCurrentUserAccess(RequestMethod[CurrentUserAccess]):
    __endpoint__ = "/api/bootstrap/{org_uuid}/current_user_access"
    __http_method__ = "GET"
    __model__ = CurrentUserAccess

    org_uuid: str

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {"path": {"org_uuid": self.org_uuid}}
