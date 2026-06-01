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


class ProductPrice(ClaudeObject):
    """One plan's price line (amounts are integer minor units / cents)."""

    basePrice: int
    totalPrice: int
    subtotalPrice: int | None = None
    proratedRefund: int | None = None
    taxAmount: int | None = None
    undiscountedPrice: int | None = None
    stripeBalanceApplied: int | None = None
    offer: Any | None = None
    offerDetails: Any | None = None


class PlanPricing(ClaudeObject):
    """individual_plan_pricing/v2 — per-plan price matrix keyed by plan id."""

    country: str | None = None
    currency: str | None = None
    product_prices_due_today: dict[str, ProductPrice] = {}
    product_prices_per_billing_period: dict[str, ProductPrice] = {}
    proration_timestamp: int | None = None
    taxDisplay: TaxDisplay | None = None
    presentment_currency: str | None = None
    presentment_amount_minor: int | None = None
    settlement_currency: str | None = None
    settlement_amount_minor: int | None = None
