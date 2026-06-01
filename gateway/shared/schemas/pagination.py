"""Page[T] + PageParams — the one pagination shape, aligned with SDK PaginatedResponse."""

from __future__ import annotations

import base64
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, field_validator

T = TypeVar("T")

MAX_LIMIT = 200


def encode_cursor(created_at: datetime, id_: str) -> str:
    """Opaque keyset cursor over the indexed ``(created_at, id)`` tuple."""
    raw = f"{created_at.isoformat()}|{id_}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[str, str]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("invalid cursor") from exc
    ts, sep, id_ = raw.partition("|")
    if not sep:
        raise ValueError("invalid cursor")
    return ts, id_


class PageParams(BaseModel):
    limit: int = 50
    offset: int = 0
    cursor: str | None = None

    @field_validator("limit")
    @classmethod
    def _clamp_limit(cls, v: int) -> int:
        return max(1, min(v, MAX_LIMIT))

    @field_validator("offset")
    @classmethod
    def _non_negative(cls, v: int) -> int:
        return max(0, v)


class Page(BaseModel, Generic[T]):
    data: list[T]
    has_more: bool
    cursor: str | None = None
    total: int | None = None
