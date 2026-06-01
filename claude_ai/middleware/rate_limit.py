"""RateLimitMiddleware: enforces a minimum interval between outgoing requests."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from claude_ai.middleware.base import Middleware, NextHandler
from claude_ai.transport.base import TransportRequest, TransportResponse


class RateLimitMiddleware(Middleware[TransportRequest, TransportResponse]):
    def __init__(self, min_interval: float = 0.5) -> None:
        self._min_interval = min_interval
        self._last_request: float = 0.0
        self._lock = asyncio.Lock()

    async def __call__(
        self,
        handler: NextHandler[TransportRequest, TransportResponse],
        event: TransportRequest,
        data: dict[str, Any],
    ) -> TransportResponse:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request
            wait = self._min_interval - elapsed if elapsed < self._min_interval else 0.0
            self._last_request = now + wait

        if wait > 0:
            await asyncio.sleep(wait)

        return await handler(event, data)
