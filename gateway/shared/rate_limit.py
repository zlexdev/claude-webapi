"""In-process per-key token-bucket rate limiter (FP-5).

Single-loop asyncio: the read-modify of a bucket has no ``await`` inside, so it is
atomic without a lock. Redis-backed distributed limiting is a documented future step.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from gateway.base.errors import GatewayError


class RateLimited(GatewayError):
    status_code = 429
    error_type = "rate_limit_error"
    message = "Rate limit exceeded — slow down"


@dataclass
class TokenBucket:
    capacity: float
    refill_per_sec: float
    tokens: float = field(default=0.0)
    last: float = field(default_factory=time.monotonic)

    def __post_init__(self) -> None:
        if self.tokens == 0.0:
            self.tokens = self.capacity

    def allow(self, cost: float = 1.0) -> bool:
        now = time.monotonic()
        self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.refill_per_sec)
        self.last = now
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False


class KeyedRateLimiter:
    """One bucket per key; ``per_min`` requests with a per-minute refill."""

    def __init__(self, per_min: int) -> None:
        self._per_min = per_min
        self._buckets: dict[str, TokenBucket] = {}

    def allow(self, key: str) -> bool:
        if self._per_min <= 0:
            return True
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = TokenBucket(capacity=float(self._per_min), refill_per_sec=self._per_min / 60.0)
            self._buckets[key] = bucket
        return bucket.allow()
