"""Organization, subscription, credits, model-config models."""

from datetime import datetime
from typing import Any

from pydantic import Field

from claude_ai.models._object import ClaudeObject

from claude_ai.enums.status import BillingInterval, SubscriptionStatus


class OrgSettings(ClaudeObject):
    claude_console_privacy: str | None = None
    claude_ai_completion_feedback_enabled: bool | None = None
    claude_code_metrics_logging_enabled: bool | None = None
    claude_code_penguin_mode_enabled: bool | None = None
    claude_ai_integration_sharing_enabled: bool | None = None
    claude_ai_chat_sharing_enabled: bool | None = None
    inline_visualizations_enabled: bool | None = None


class Organization(ClaudeObject):
    id: int
    uuid: str
    name: str
    settings: OrgSettings = OrgSettings()
    join_token: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    active_flags: list[str] = []
    capabilities: list[str] = []
    rate_limit_tier: str | None = None


class PaymentMethod(ClaudeObject):
    brand: str | None = None
    country: str | None = None
    last4: str | None = None
    type: str | None = None


class SubscriptionDetails(ClaudeObject):
    status: SubscriptionStatus | None = None
    billing_interval: BillingInterval | None = None
    next_charge_date: str | None = None
    payment_method: PaymentMethod | None = None
    has_schedule: bool = False
    has_discounts: bool = False
    plan_ending_before: str | None = None
    trial_end_ts: str | None = None
    scheduled_downgrade: Any | None = None


class Credits(ClaudeObject):
    remaining: float = 0.0
    total: float = 0.0


class ModelConfig(ClaudeObject):
    api_model: str
    image_in: bool = False
    pdf_in: bool = False
    max_tokens_cap: int = 128000


class Style(ClaudeObject):
    uuid: str = ""
    key: str | None = None
    type: str | None = None
    name: str
    description: str | None = None
    content: str | None = None
    prompt: str | None = None
    summary: str | None = None
    is_default: bool | None = None

    def model_post_init(self, _ctx: Any) -> None:
        if not self.uuid and self.key:
            self.uuid = self.key


class Memory(ClaudeObject):
    memories: list[dict[str, Any]] = []


class FeaturePreference(ClaudeObject):
    enable_email: bool | None = None
    enable_push: bool | None = None


class PushReachability(ClaudeObject):
    has_active_channel: bool = False
    platforms: list[Any] = []  # element shape unobserved (empty live)
    most_recent_token_refresh: str | None = None


class NotificationPreferenceSet(ClaudeObject):
    # one entry per Claude feature (assist, compass, completion, dispatch, marketing, …)
    feature_preference: dict[str, FeaturePreference] = {}


class NotificationPreferences(ClaudeObject):
    account_id: int
    organization_id: int
    preferences: NotificationPreferenceSet = NotificationPreferenceSet()
    push_reachability: PushReachability = PushReachability()


class Experience(ClaudeObject):
    id: str
    key: str
    placement_key: str
    variant_key: str
    exp_id: str
    enabled: bool = False
    template_key: str | None = None
    content: dict[str, Any] = {}  # variant-defined payload
    config: dict[str, Any] = {}


class RateLimit(ClaudeObject):
    remaining: int = 0
    reset_at: datetime | None = None


class GlobalRules(ClaudeObject):
    rate_limit: RateLimit | None = None
    cooldown: Any | None = None


class ExperienceRules(ClaudeObject):
    global_: GlobalRules | None = Field(default=None, alias="global")
    placements: dict[str, Any] = {}
    tiers: dict[str, Any] = {}


class Experiences(ClaudeObject):
    experiences: list[Experience] = []
    rules: ExperienceRules | None = None
