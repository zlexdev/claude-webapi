"""Bootstrap / current-user access models."""

from typing import Any

from claude_ai.models._object import ClaudeObject


class AccessFeature(ClaudeObject):
    feature: str
    status: str | None = None


class CurrentUserAccess(ClaudeObject):
    account_features: list[AccessFeature] = []
    account_permissions: list[Any] = []
    features: list[AccessFeature] = []
