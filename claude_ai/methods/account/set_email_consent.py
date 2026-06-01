"""SetEmailConsent: record marketing-email consent."""

from typing import Any

from claude_ai.enums.billing import ConsentVariant
from claude_ai.methods.base import RequestMethod


class SetEmailConsent(RequestMethod[None]):
    __endpoint__ = "/api/account/email_consent"
    __http_method__ = "PUT"
    __model__ = type(None)

    consent: bool = True
    accepted_via_checkbox: bool = True
    variant: ConsentVariant = ConsentVariant.NOTICES

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {
            "body": {
                "consent": self.consent,
                "accepted_via_checkbox": self.accepted_via_checkbox,
                "variant": self.variant,
            }
        }
