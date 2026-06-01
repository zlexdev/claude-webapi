"""BaseRepo[TRow]: generic async CRUD + keyset cursor pagination over SQLAlchemy rows.

Every array read goes through :meth:`page` / :meth:`iterate_all`, which seek past an
opaque ``(created_at, id)`` cursor and ``LIMIT`` — never ``OFFSET`` — so deep pages stay
O(limit). The ``(created_at, id)`` composite index on each table backs the seek.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from datetime import datetime
from typing import Any, ClassVar, Generic, TypeVar

from sqlalchemy import ColumnElement, select, tuple_

from gateway.shared.db.engine import Database
from gateway.shared.db.orm import BaseOrm
from gateway.shared.schemas.pagination import decode_cursor, encode_cursor

TRow = TypeVar("TRow", bound=BaseOrm)


class BaseRepo(Generic[TRow]):
    model: ClassVar[type[BaseOrm]]

    def __init__(self, db: Database) -> None:
        self._db = db

    async def get(self, id_: str) -> TRow | None:
        async with self._db.session() as s:
            return await s.get(self.model, id_)  # type: ignore[return-value]

    async def get_by(self, column: ColumnElement[Any], value: Any) -> TRow | None:
        async with self._db.session() as s:
            result = await s.execute(select(self.model).where(column == value).limit(1))
            return result.scalar_one_or_none()  # type: ignore[no-any-return]

    async def upsert(self, row: TRow) -> None:
        async with self._db.session() as s:
            await s.merge(row)
            await s.commit()

    async def page(
        self,
        *,
        limit: int,
        cursor: str | None = None,
        where: Sequence[ColumnElement[bool]] = (),
    ) -> tuple[list[TRow], str | None, bool]:
        stmt = select(self.model)
        for clause in where:
            stmt = stmt.where(clause)
        if cursor:
            ts, id_ = decode_cursor(cursor)
            stmt = stmt.where(
                tuple_(self.model.created_at, self.model.id)  # type: ignore[attr-defined]
                < (datetime.fromisoformat(ts), id_)
            )
        stmt = stmt.order_by(
            self.model.created_at.desc(),  # type: ignore[attr-defined]
            self.model.id.desc(),  # type: ignore[attr-defined]
        ).limit(limit + 1)
        async with self._db.session() as s:
            rows = list((await s.execute(stmt)).scalars().all())
        has_more = len(rows) > limit
        rows = rows[:limit]
        next_cursor = (
            encode_cursor(rows[-1].created_at, rows[-1].id) if has_more and rows else None
        )
        return rows, next_cursor, has_more

    async def iterate_all(
        self, *, batch: int = 500, where: Sequence[ColumnElement[bool]] = ()
    ) -> AsyncIterator[TRow]:
        cursor: str | None = None
        while True:
            rows, cursor, has_more = await self.page(limit=batch, cursor=cursor, where=where)
            for row in rows:
                yield row
            if not has_more or cursor is None:
                break

    async def delete(self, id_: str) -> None:
        async with self._db.session() as s:
            obj = await s.get(self.model, id_)
            if obj is not None:
                await s.delete(obj)
                await s.commit()
