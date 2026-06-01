"""VerifyGoogle: complete a Google OAuth login (code + Arkose session token)."""

from typing import Any

from claude_ai.enums.auth import Locale, SourceApp
from claude_ai.methods.base import RequestMethod


class VerifyGoogle(RequestMethod[None]):
    __endpoint__ = "/api/auth/verify_google"
    __http_method__ = "POST"
    __model__ = type(None)

    code: str
    arkose_session_token: str
    locale: Locale = Locale.EN_US
    source: SourceApp = SourceApp.CLAUDE
    return_to: str | None = None

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {
            "body": {
                "code": self.code,
                "locale": self.locale,
                "return_to": self.return_to,
                "arkose_session_token": self.arkose_session_token,
                "source": self.source,
            }
        }
