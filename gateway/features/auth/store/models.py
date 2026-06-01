"""SQLAlchemy ORM rows for the auth tables (Postgres backend only).

Whole DTO lives in ``data`` JSONB; ``key_hash`` / ``account_id`` / ``revoked`` / ``tier``
are promoted to indexed columns. ``(created_at, id)`` composite index backs keyset
pagination. Imported only by the Postgres store (lazy).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from gateway.shared.db.orm import BaseOrm, TimestampMixin


class AccountRow(BaseOrm, TimestampMixin):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    tier: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    __table_args__ = (Index("ix_accounts_keyset", "created_at", "id"),)


class ApiKeyRow(BaseOrm, TimestampMixin):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    key_hash: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    account_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (Index("ix_api_keys_keyset", "created_at", "id"),)
