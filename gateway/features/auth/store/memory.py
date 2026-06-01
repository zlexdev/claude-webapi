"""In-memory auth stores (tests + CLAUDE_GATEWAY_DB=memory).

Cursor pagination mirrors the Postgres keyset exactly: order by ``(created_at, id)``
descending, seek strictly past the decoded cursor — so behaviour is identical across
backends and the route-contract tests hold regardless of ``CLAUDE_GATEWAY_DB``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import TypeVar

from gateway.features.auth.schemas.dtos import Account, ApiKey
from gateway.features.auth.store.base import BaseAccountStore, BaseApiKeyStore
from gateway.shared.schemas.pagination import Page, decode_cursor, encode_cursor

T = TypeVar("T")


def _paginate(rows: list[tuple[datetime, str, T]], limit: int, cursor: str | None) -> Page[T]:
    rows.sort(key=lambda r: (r[0], r[1]), reverse=True)
    if cursor:
        ts, cid = decode_cursor(cursor)
        anchor = (datetime.fromisoformat(ts), cid)
        rows = [r for r in rows if (r[0], r[1]) < anchor]
    has_more = len(rows) > limit
    page_rows = rows[:limit]
    next_cursor = (
        encode_cursor(page_rows[-1][0], page_rows[-1][1]) if has_more and page_rows else None
    )
    return Page(data=[r[2] for r in page_rows], has_more=has_more, cursor=next_cursor)


class MemoryApiKeyStore(BaseApiKeyStore):
    def __init__(self) -> None:
        self._by_id: dict[str, ApiKey] = {}

    async def create(self, key: ApiKey) -> None:
        self._by_id[key.key_id] = key

    async def get(self, key_id: str) -> ApiKey | None:
        return self._by_id.get(key_id)

    async def get_by_hash(self, key_hash: str) -> ApiKey | None:
        for key in self._by_id.values():
            if key.key_hash == key_hash:
                return key
        return None

    async def page(
        self, *, account_id: str | None = None, limit: int = 50, cursor: str | None = None
    ) -> Page[ApiKey]:
        rows = [
            (k.created_at, k.key_id, k)
            for k in self._by_id.values()
            if account_id is None or k.account_id == account_id
        ]
        return _paginate(rows, limit, cursor)

    async def revoke(self, key_id: str) -> None:
        key = self._by_id.get(key_id)
        if key is not None:
            self._by_id[key_id] = key.model_copy(update={"revoked": True})

    async def touch(self, key_id: str, when: datetime) -> None:
        key = self._by_id.get(key_id)
        if key is not None:
            self._by_id[key_id] = key.model_copy(update={"last_used_at": when})

    async def close(self) -> None:
        return None


class MemoryAccountStore(BaseAccountStore):
    def __init__(self) -> None:
        self._by_id: dict[str, Account] = {}

    async def upsert(self, account: Account) -> None:
        self._by_id[account.account_id] = account

    async def get(self, account_id: str) -> Account | None:
        return self._by_id.get(account_id)

    async def page(
        self, *, include_revoked: bool = False, limit: int = 50, cursor: str | None = None
    ) -> Page[Account]:
        rows = [
            (a.created_at, a.account_id, a)
            for a in self._by_id.values()
            if include_revoked or not a.revoked
        ]
        return _paginate(rows, limit, cursor)

    async def iterate_all(self, *, include_revoked: bool = False) -> AsyncIterator[Account]:
        cursor: str | None = None
        while True:
            page = await self.page(include_revoked=include_revoked, limit=500, cursor=cursor)
            for account in page.data:
                yield account
            if not page.has_more or page.cursor is None:
                break
            cursor = page.cursor

    async def revoke(self, account_id: str) -> None:
        account = self._by_id.get(account_id)
        if account is not None:
            self._by_id[account_id] = account.model_copy(update={"revoked": True})

    async def close(self) -> None:
        return None
