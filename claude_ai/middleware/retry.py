"""RetryMiddleware: exponential backoff with idempotency guard. POST/DELETE/PATCH skipped unless retry_non_idempotent=True."""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

import httpx

from claude_ai.middleware.base import Middleware, NextHandler
from claude_ai.transport.base import TransportRequest, TransportResponse

logger = logging.getLogger("claude_ai")

RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})
RETRYABLE_EXCEPTIONS = (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout)
IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "PUT", "DELETE"})


class RetryMiddleware(Middleware[TransportRequest, TransportResponse]):
    def __init__(
        self,
        max_retries: int = 3,
        backoff: float = 1.0,
        *,
        retry_non_idempotent: bool = False,
    ) -> None:
        self._max_retries = max_retries
        self._backoff = backoff
        self._retry_non_idempotent = retry_non_idempotent

    async def __call__(
        self,
        handler: NextHandler[TransportRequest, TransportResponse],
        event: TransportRequest,
        data: dict[str, Any],
    ) -> TransportResponse:
        method = event.method.upper()
        idempotent = method in IDEMPOTENT_METHODS or self._retry_non_idempotent

        last_response: TransportResponse | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = await handler(event, data)
            except RETRYABLE_EXCEPTIONS:
                if attempt == self._max_retries or not idempotent:
                    raise
                await asyncio.sleep(self._delay(attempt))
                continue

            if (
                not idempotent
                or response.status_code not in RETRYABLE_STATUSES
                or attempt == self._max_retries
            ):
                return response

            last_response = response
            delay = self._parse_retry_after(response, attempt)
            logger.warning(
                "Retry %d/%d for %s %s [%d], wait %.1fs",
                attempt + 1,
                self._max_retries,
                event.method,
                event.url,
                response.status_code,
                delay,
            )
            await asyncio.sleep(delay)

        if last_response is None:
            raise RuntimeError("Retry loop exited without response or exception")
        return last_response

    def _parse_retry_after(self, response: TransportResponse, attempt: int) -> float:
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                pass
        return self._delay(attempt)

    def _delay(self, attempt: int) -> float:
        return self._backoff * (2**attempt) + random.uniform(0, 0.5)
