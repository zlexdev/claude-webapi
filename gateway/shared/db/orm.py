"""BaseOrm + TimestampMixin — SQLAlchemy 2.0 declarative base for gateway tables.

Every table carries ``created_at / updated_at / version`` (the mixin) plus an ``id``
PK and a ``data`` JSONB body on the concrete model. ``(created_at, id)`` is the keyset
index used by every paginated read (see ``repo.BaseRepo.page``).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class BaseOrm(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
