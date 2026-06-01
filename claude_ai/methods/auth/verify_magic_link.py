"""VerifyMagicLink: exchange a magic-link nonce (or fallback code) for a session.

On success claude.ai sets session cookies (absorbed by HttpSession) and returns
the bootstrap account blob plus the activity `secret`.
"""

from typing import Any

from claude_ai.enums.auth import CredentialMethod, Locale, SourceApp
from claude_ai.methods.base import RequestMethod
from claude_ai.models.auth import AuthResult


class VerifyMagicLink(RequestMethod[AuthResult]):
    __endpoint__ = "/api/auth/verify_magic_link"
    __http_method__ = "POST"
    __model__ = AuthResult

    method: CredentialMethod = CredentialMethod.NONCE
    nonce: str | None = None
    encoded_email_address: str | None = None
    code: str | None = None
    locale: Locale = Locale.EN_US
    source: SourceApp = SourceApp.CLAUDE

    def build_params(self, params: Any = None) -> dict[str, Any]:
        credentials: dict[str, Any] = {"method": self.method}
        if self.nonce is not None:
            credentials["nonce"] = self.nonce
        if self.encoded_email_address is not None:
            credentials["encoded_email_address"] = self.encoded_email_address
        if self.code is not None:
            credentials["code"] = self.code
        return {
            "body": {
                "credentials": credentials,
                "locale": self.locale,
                "source": self.source,
            }
        }
