"""GetProfile: current account profile."""

from typing import Any

from claude_ai.methods.base import BaseMethod
from claude_ai.models.account import AccountProfile


class GetProfile(BaseMethod[None, AccountProfile]):
    __endpoint__ = "/api/account_profile"
    __http_method__ = "GET"
    __model__ = AccountProfile

    def build_params(self, params: None) -> dict[str, Any]:
        return {}
