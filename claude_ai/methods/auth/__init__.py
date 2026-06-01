"""Authentication endpoints (login methods, magic link, Google OAuth)."""

from claude_ai.methods.auth.exchange_nonce_for_code import ExchangeNonceForCode
from claude_ai.methods.auth.get_login_methods import GetLoginMethods
from claude_ai.methods.auth.send_magic_link import SendMagicLink
from claude_ai.methods.auth.verify_google import VerifyGoogle
from claude_ai.methods.auth.verify_magic_link import VerifyMagicLink

__all__ = [
    "GetLoginMethods",
    "SendMagicLink",
    "VerifyMagicLink",
    "ExchangeNonceForCode",
    "VerifyGoogle",
]
