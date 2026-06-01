"""Proxy-related events (invalid proxy notifications)."""

from __future__ import annotations

from claude_ai.events.base import BaseEvent


class ProxyInvalidEvent(BaseEvent):
    type: str = "proxy.invalid"
    proxy_url: str = ""
    reason: str = ""
