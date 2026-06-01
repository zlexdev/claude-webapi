"""ListSkills: skills available / enabled for an org."""

from typing import Any

from claude_ai.methods.base import RequestMethod
from claude_ai.models.settings import SkillList


class ListSkills(RequestMethod[SkillList]):
    __endpoint__ = "/api/organizations/{org_uuid}/skills/list-skills"
    __http_method__ = "GET"
    __model__ = SkillList

    org_uuid: str

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {"path": {"org_uuid": self.org_uuid}}
