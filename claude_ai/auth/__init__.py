"""Auth module: dynamically refreshable shared authentication."""

from claude_ai.auth.base import BaseAuth
from claude_ai.auth.cookie_auth import CookieAuth

__all__ = ["BaseAuth", "CookieAuth"]
