"""Orchestrator enums: account tier (routing) + batch job/item status."""

from enum import IntEnum, StrEnum


class AccountTier(IntEnum):
    """Higher = more capable. Used as a `>=` floor filter in `pick(min_tier=...)`."""

    FREE = 0
    PRO = 1
    MAX = 2


class BatchItemStatus(StrEnum):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"


class BatchStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"  # finished with some failed items
