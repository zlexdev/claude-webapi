"""GetCoworkSettings: cowork (agent workspace) enablement settings for an org."""

from typing import Any

from claude_ai.methods.base import RequestMethod
from claude_ai.models.settings import CoworkSettings


class GetCoworkSettings(RequestMethod[CoworkSettings]):
    __endpoint__ = "/api/organizations/{org_uuid}/cowork_settings"
    __http_method__ = "GET"
    __model__ = CoworkSettings

    org_uuid: str

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {"path": {"org_uuid": self.org_uuid}}
