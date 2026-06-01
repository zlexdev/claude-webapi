"""HttpMiddleware alias for Middleware[TransportRequest, TransportResponse]."""

from __future__ import annotations

from claude_ai.middleware.base import Middleware
from claude_ai.transport.base import TransportRequest, TransportResponse

HttpMiddleware = Middleware[TransportRequest, TransportResponse]
