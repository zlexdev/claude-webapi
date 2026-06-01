"""Login-flow errors."""

from __future__ import annotations

from claude_ai.exceptions import ClaudeAIError


class LoginError(ClaudeAIError):  # type: ignore[misc]  # ClaudeAIError is Any under the SDK mypy silence
    """Magic-link login could not be completed (bad link, failed verification)."""
