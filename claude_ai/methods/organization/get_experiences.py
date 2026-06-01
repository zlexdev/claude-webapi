"""GetExperiences: web-experience (in-app placement / nudge) config for an org."""

from typing import Any

from claude_ai.enums.auth import Locale
from claude_ai.methods.base import RequestMethod
from claude_ai.models.organization import Experiences


class GetExperiences(RequestMethod[Experiences]):
    __endpoint__ = "/api/organizations/{org_uuid}/experiences/claude_web"
    __http_method__ = "GET"
    __model__ = Experiences

    org_uuid: str
    locale: Locale = Locale.EN_US

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {
            "path": {"org_uuid": self.org_uuid},
            "query": {"locale": self.locale},
        }
