"""GetNotificationPreferences: per-feature email/push notification matrix.

The preference matrix nests one entry per Claude feature (assist, compass,
completion, dispatch, marketing, ...) — returned raw as ``dict``.
"""

from typing import Any

from claude_ai.methods.base import RequestMethod


class GetNotificationPreferences(RequestMethod[dict[str, Any]]):
    __endpoint__ = "/api/organizations/{org_uuid}/notification/preferences"
    __http_method__ = "GET"
    __model__ = dict

    org_uuid: str

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {"path": {"org_uuid": self.org_uuid}}
