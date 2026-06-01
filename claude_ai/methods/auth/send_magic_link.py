"""SendMagicLink: trigger a login email (with fallback numeric code config)."""

from typing import Any

from claude_ai.enums.auth import Locale, SourceApp
from claude_ai.methods.base import RequestMethod
from claude_ai.models.auth import MagicLinkResult


class SendMagicLink(RequestMethod[MagicLinkResult]):
    __endpoint__ = "/api/auth/send_magic_link"
    __http_method__ = "POST"
    __model__ = MagicLinkResult

    email_address: str
    locale: Locale = Locale.EN_US
    source: SourceApp = SourceApp.CLAUDE
    utc_offset: int = 0
    login_intent: str | None = None
    return_to: str | None = None

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {
            "body": {
                "utc_offset": self.utc_offset,
                "email_address": self.email_address,
                "login_intent": self.login_intent,
                "locale": self.locale,
                "return_to": self.return_to,
                "source": self.source,
            }
        }
