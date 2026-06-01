"""Generic status / role / billing / provider / rendering enums."""

from enum import StrEnum


class FeatureStatus(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    TRIALING = "trialing"


class BillingInterval(StrEnum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class SyncProvider(StrEnum):
    GITHUB = "github"
    GMAIL = "gmail"
    GCAL = "gcal"
    MCP_DRIVE = "mcp/drive"
    GDRIVE = "gdrive"


class ConversationPlatform(StrEnum):
    WEB = "web"
    MOBILE = "mobile"
    API = "api"


class RenderingMode(StrEnum):
    MESSAGES = "messages"
    RAW = "raw"
