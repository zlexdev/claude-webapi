"""Auth-flow models: login methods, magic-link config, verification result."""

from typing import Any

from claude_ai.models._object import ClaudeObject


class LoginMethods(ClaudeObject):
    methods: list[str] = []


class FallbackCodeConfig(ClaudeObject):
    charset: str | None = None
    length: int | None = None
    show_input_after_delay: int | None = None


class MagicLinkResult(ClaudeObject):
    sent: bool = False
    sso_url: str | None = None
    magic_link_intent_available: Any | None = None
    sso_browser_requirement: Any | None = None
    fallback_code_configuration: FallbackCodeConfig | None = None


class AuthResult(ClaudeObject):
    """Result of verify_magic_link / exchange_nonce_for_code.

    `account` is the bootstrap account blob — left as a raw dict because it
    duplicates the full account/membership tree returned by GetProfile and is
    not worth a second brittle model.
    """

    success: bool = False
    secret: str | None = None
    account: dict[str, Any] | None = None
