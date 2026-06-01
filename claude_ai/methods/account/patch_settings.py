"""PatchAccountSettings: partial update of account settings (PATCH /api/account/settings)."""

from typing import Any

from claude_ai.methods.base import RequestMethod


class PatchAccountSettings(RequestMethod[None]):
    __endpoint__ = "/api/account/settings"
    __http_method__ = "PATCH"
    __model__ = type(None)

    settings: dict[str, Any]

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {"body": self.settings}
