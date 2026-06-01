"""ExchangeNonceForCode: trade a magic-link nonce for an OAuth-style login code."""

from typing import Any

from claude_ai.enums.auth import CredentialMethod, Locale, SourceApp
from claude_ai.methods.base import RequestMethod
from claude_ai.models.auth import AuthResult


class ExchangeNonceForCode(RequestMethod[AuthResult]):
    __endpoint__ = "/api/auth/exchange_nonce_for_code"
    __http_method__ = "POST"
    __model__ = AuthResult

    nonce: str
    encoded_email_address: str | None = None
    method: CredentialMethod = CredentialMethod.NONCE
    locale: Locale = Locale.EN_US
    source: SourceApp = SourceApp.CLAUDE

    def build_params(self, params: Any = None) -> dict[str, Any]:
        credentials: dict[str, Any] = {"method": self.method, "nonce": self.nonce}
        if self.encoded_email_address is not None:
            credentials["encoded_email_address"] = self.encoded_email_address
        return {
            "body": {
                "credentials": credentials,
                "locale": self.locale,
                "source": self.source,
            }
        }
