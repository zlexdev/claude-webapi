"""Database: the single async engine + sessionmaker (SQLAlchemy 2.0).

One per process, built in the app container when ``CLAUDE_GATEWAY_DB=postgres``.
``database_url`` must use an async driver, e.g. ``postgresql+asyncpg://user:pw@host/db``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from gateway.shared.db.orm import BaseOrm
from gateway.shared.logging import get_logger

log = get_logger("db.engine")


class Database:
    def __init__(self, url: str, *, echo: bool = False, pool_size: int = 10) -> None:
        self._engine: AsyncEngine = create_async_engine(
            url, echo=echo, pool_pre_ping=True, pool_size=pool_size
        )
        self._sessionmaker = async_sessionmaker(
            self._engine, expire_on_commit=False, class_=AsyncSession
        )

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self._sessionmaker() as session:
            yield session

    async def create_all(self) -> None:
        """Idempotent schema bootstrap (additive). Alembic owns destructive changes."""
        async with self._engine.begin() as conn:
            await conn.run_sync(BaseOrm.metadata.create_all)
        log.info("schema ensured")

    async def close(self) -> None:
        await self._engine.dispose()
