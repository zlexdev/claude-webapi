"""UpdateAccountSettings: replace the account-level settings blob (PUT /api/account)."""

from typing import Any

from claude_ai.methods.base import RequestMethod


class UpdateAccountSettings(RequestMethod[dict[str, Any]]):
    __endpoint__ = "/api/account"
    __http_method__ = "PUT"
    __model__ = dict

    settings: dict[str, Any]

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {"body": {"settings": self.settings}}
