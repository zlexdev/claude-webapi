"""Email magic-link login flow: request a link, complete it into session cookies.

    from claude_ai.login import MagicLinkLogin

    async with MagicLinkLogin() as login:
        await login.request("user@example.com")          # sends the email
        # ... user clicks the link in their inbox ...
        result = await login.complete("https://claude.ai/magic-link/<encoded>/<nonce>")
        result.cookies    # -> dict[str, str] ready for ClaudeAIClient(session=HttpSession(cookies=...))
        result.org_uuid   # bootstrapped from the verify response
"""

from claude_ai.login.errors import LoginError
from claude_ai.login.link import ParsedLink, encode_email, parse_magic_link
from claude_ai.login.result import LoginResult
from claude_ai.login.session import MagicLinkLogin

__all__ = [
    "LoginError",
    "LoginResult",
    "MagicLinkLogin",
    "ParsedLink",
    "encode_email",
    "parse_magic_link",
]
