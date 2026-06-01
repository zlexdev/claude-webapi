"""LoggingMiddleware: HTTP method/url/status/elapsed-time logging."""

from __future__ import annotations

import logging
import time
from typing import Any

from claude_ai.middleware.base import Middleware, NextHandler
from claude_ai.transport.base import TransportRequest, TransportResponse

logger = logging.getLogger("claude_ai")


class LoggingMiddleware(Middleware[TransportRequest, TransportResponse]):
    async def __call__(
        self,
        handler: NextHandler[TransportRequest, TransportResponse],
        event: TransportRequest,
        data: dict[str, Any],
    ) -> TransportResponse:
        logger.debug("-> %s %s", event.method, event.url)
        start = time.monotonic()
        response = await handler(event, data)
        elapsed = time.monotonic() - start
        logger.debug(
            "<- %s %s [%d] %.2fs",
            event.method,
            event.url,
            response.status_code,
            elapsed,
        )
        return response
