"""GetLoginMethods: available login methods for an email (google / magic_link)."""

from typing import Any

from claude_ai.enums.auth import SourceApp
from claude_ai.methods.base import RequestMethod
from claude_ai.models.auth import LoginMethods


class GetLoginMethods(RequestMethod[LoginMethods]):
    __endpoint__ = "/api/auth/login_methods"
    __http_method__ = "GET"
    __model__ = LoginMethods

    email: str
    source: SourceApp = SourceApp.CLAUDE

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {"query": {"email": self.email, "source": self.source}}
