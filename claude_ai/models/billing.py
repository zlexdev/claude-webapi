"""Billing / Stripe pricing models.

Billing endpoints use camelCase wire field names (unlike the snake_case
claude.ai core API); the model fields mirror the wire verbatim.
"""

from typing import Any

from claude_ai.models._object import ClaudeObject


class StripeRegion(ClaudeObject):
    stripe_region: str | None = None


class Eligibility(ClaudeObject):
    eligible: bool = False
    reason: str | None = None


class TaxDisplay(ClaudeObject):
    show_included: bool | None = None
    tax_label: str | None = None


class ConsumerPricing(ClaudeObject):
    country: str | None = None
    currency: str | None = None
    price: int | None = None
    taxAmount: int | None = None
    undiscountedPrice: int | None = None
    undiscountedTaxAmount: int | None = None
    stripeBalanceToBeApplied: int | None = None
    offer: Any | None = None
    offerDetails: Any | None = None
    trialInfo: Any | None = None
    promotionStatus: Any | None = None
    taxDisplay: TaxDisplay | None = None


class StripeIntent(ClaudeObject):
    clientSecret: str | None = None
    entity: str | None = None
    existingPaymentMethod: Any | None = None
    setupIntentId: str | None = None


class PausedSubscription(ClaudeObject):
    plan_type: str | None = None
    currency: str | None = None
    price: int | None = None
    payment_paused_until: str | None = None
    manual_pause_scheduled_at: str | None = None
