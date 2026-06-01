"""Miscellaneous account-level endpoints (referral, team eligibility)."""

from claude_ai.methods.misc.check_team_signup_eligibility import (
    CheckTeamSignupEligibility,
)
from claude_ai.methods.misc.check_team_trial_eligibility import (
    CheckTeamTrialEligibility,
)
from claude_ai.methods.misc.get_referral import GetReferral

__all__ = [
    "GetReferral",
    "CheckTeamSignupEligibility",
    "CheckTeamTrialEligibility",
]
