"""Billing / subscription flow enums."""

from enum import StrEnum


class BillingPlan(StrEnum):
    PRO = "pro"
    MAX_5X = "max_5x"
    MAX_20X = "max_20x"


class ConsentVariant(StrEnum):
    NOTICES = "notices"


class EligibilityCheck(StrEnum):
    TEAM_VOUCHER = "voucher-eligible"
    TEAM_TRIAL_EXPOSURE = "exposure-eligible"
