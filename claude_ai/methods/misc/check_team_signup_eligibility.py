"""CheckTeamSignupEligibility: whether the account may use a team-signup voucher."""

from typing import Any

from claude_ai.enums.billing import EligibilityCheck
from claude_ai.methods.base import RequestMethod
from claude_ai.models.billing import Eligibility


class CheckTeamSignupEligibility(RequestMethod[Eligibility]):
    __endpoint__ = "/api/team-signup/{check}"
    __http_method__ = "GET"
    __model__ = Eligibility

    check: EligibilityCheck = EligibilityCheck.TEAM_VOUCHER

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {"path": {"check": self.check}}
