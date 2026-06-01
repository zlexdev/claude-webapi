"""UpdateProfile: patch the account profile (work function, locale, preferences)."""

from typing import Any

from claude_ai.methods.base import RequestMethod
from claude_ai.models.account import AccountProfile


class UpdateProfile(RequestMethod[AccountProfile]):
    __endpoint__ = "/api/account_profile"
    __http_method__ = "PUT"
    __model__ = AccountProfile

    work_function: str | None = None
    locale: str | None = None
    conversation_preferences: str | None = None

    def build_params(self, params: Any = None) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if self.work_function is not None:
            body["work_function"] = self.work_function
        if self.locale is not None:
            body["locale"] = self.locale
        if self.conversation_preferences is not None:
            body["conversation_preferences"] = self.conversation_preferences
        return {"body": body}
