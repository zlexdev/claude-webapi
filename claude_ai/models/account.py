"""Account profile and access info models."""

from claude_ai.models._object import ClaudeObject

from claude_ai.enums.status import FeatureStatus


class AccountProfile(ClaudeObject):
    work_function: str | None = None
    conversation_preferences: str | None = None
    locale: str | None = None
    onboarding_topics: list[str] = []
    avatar: str | None = None
    pixel_avatar: str | None = None


class Feature(ClaudeObject):
    feature: str
    status: FeatureStatus


class AccessInfo(ClaudeObject):
    features: list[Feature] = []


class RavenEligibility(ClaudeObject):
    eligible: bool = False
