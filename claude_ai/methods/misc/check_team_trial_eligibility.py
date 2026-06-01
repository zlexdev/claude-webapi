"""CheckTeamTrialEligibility: whether the account is exposed to a team-trial offer."""

from typing import Any

from claude_ai.enums.billing import EligibilityCheck
from claude_ai.methods.base import RequestMethod
from claude_ai.models.billing import Eligibility


class CheckTeamTrialEligibility(RequestMethod[Eligibility]):
    __endpoint__ = "/api/team-trial/{check}"
    __http_method__ = "GET"
    __model__ = Eligibility

    check: EligibilityCheck = EligibilityCheck.TEAM_TRIAL_EXPOSURE

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {"path": {"check": self.check}}
