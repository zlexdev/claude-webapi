"""GetExperiences: web-experience (in-app placement / nudge) config for an org.

The experiences payload is an A/B placement tree that changes constantly —
returned raw as ``dict``.
"""

from typing import Any

from claude_ai.enums.auth import Locale
from claude_ai.methods.base import RequestMethod


class GetExperiences(RequestMethod[dict[str, Any]]):
    __endpoint__ = "/api/organizations/{org_uuid}/experiences/claude_web"
    __http_method__ = "GET"
    __model__ = dict

    org_uuid: str
    locale: Locale = Locale.EN_US

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {
            "path": {"org_uuid": self.org_uuid},
            "query": {"locale": self.locale},
        }
