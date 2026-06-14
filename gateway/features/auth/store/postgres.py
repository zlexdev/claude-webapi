"""Postgres-backed auth stores (SQLAlchemy). Production default.

Maps the domain DTO whole into ``data`` JSONB and keeps promoted columns
(``key_hash`` / ``account_id`` / ``revoked`` / ``tier`` / ``created_at``) in sync via the
single :meth:`upsert` path. Imported lazily (pulls SQLAlchemy).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

from gateway.features.auth.cipher import CookieCipher
from gateway.features.auth.errors import CookieDecryptError
from gateway.features.auth.schemas.dtos import Account, ApiKey
from gateway.features.auth.store.base import BaseAccountStore, BaseApiKeyStore
from gateway.features.auth.store.models import AccountRow, ApiKeyRow
from gateway.shared.db.engine import Database
from gateway.shared.db.repo import BaseRepo
from gateway.shared.schemas.pagination import Page


class _AccountRepo(BaseRepo[AccountRow]):
    model = AccountRow


class _ApiKeyRepo(BaseRepo[ApiKeyRow]):
    model = ApiKeyRow


class PostgresAccountStore(BaseAccountStore):
    def __init__(self, db: Database, *, cipher: CookieCipher | None = None) -> None:
        self._repo = _AccountRepo(db)
        self._cipher = cipher

    def _row(self, account: Account) -> AccountRow:
        data = account.model_dump(mode="json")
        if self._cipher is not None:  # dict -> Fernet str token at rest
            data["cookies"] = self._cipher.encrypt(account.cookies)
        return AccountRow(
            id=account.account_id,
            data=data,
            tier=int(account.tier),
            revoked=account.revoked,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )

    def _dto(self, row: AccountRow) -> Account:
        data = row.data
        # A str cookies field is an encrypted token; a dict is legacy plaintext that
        # predates the key and passes straight through (re-saving migrates it).
        if isinstance(data.get("cookies"), str):
            if self._cipher is None:
                raise CookieDecryptError(
                    "cookies are encrypted at rest but no COOKIE_ENCRYPTION_KEY is set"
                )
            data = {**data, "cookies": self._cipher.decrypt(data["cookies"])}
        return Account.model_validate(data)

    async def upsert(self, account: Account) -> None:
        await self._repo.upsert(self._row(account))

    async def get(self, account_id: str) -> Account | None:
        row = await self._repo.get(account_id)
        return self._dto(row) if row else None

    async def page(
        self, *, include_revoked: bool = False, limit: int = 50, cursor: str | None = None
    ) -> Page[Account]:
        where = () if include_revoked else (AccountRow.revoked.is_(False),)
        rows, next_cursor, has_more = await self._repo.page(
            limit=limit, cursor=cursor, where=where
        )
        return Page(data=[self._dto(r) for r in rows], has_more=has_more, cursor=next_cursor)

    async def iterate_all(self, *, include_revoked: bool = False) -> AsyncIterator[Account]:
        where = () if include_revoked else (AccountRow.revoked.is_(False),)
        async for row in self._repo.iterate_all(where=where):
            yield self._dto(row)

    async def revoke(self, account_id: str) -> None:
        account = await self.get(account_id)
        if account is not None:
            await self.upsert(
                account.model_copy(update={"revoked": True, "updated_at": datetime.now(UTC)})
            )

    async def close(self) -> None:
        return None


class PostgresApiKeyStore(BaseApiKeyStore):
    def __init__(self, db: Database) -> None:
        self._repo = _ApiKeyRepo(db)

    @staticmethod
    def _row(key: ApiKey) -> ApiKeyRow:
        return ApiKeyRow(
            id=key.key_id,
            data=key.model_dump(mode="json"),
            key_hash=key.key_hash,
            account_id=key.account_id,
            revoked=key.revoked,
            created_at=key.created_at,
            updated_at=key.created_at,
        )

    @staticmethod
    def _dto(row: ApiKeyRow) -> ApiKey:
        return ApiKey.model_validate(row.data)

    async def create(self, key: ApiKey) -> None:
        await self._repo.upsert(self._row(key))

    async def get(self, key_id: str) -> ApiKey | None:
        row = await self._repo.get(key_id)
        return self._dto(row) if row else None

    async def get_by_hash(self, key_hash: str) -> ApiKey | None:
        row = await self._repo.get_by(ApiKeyRow.key_hash, key_hash)
        return self._dto(row) if row else None

    async def page(
        self, *, account_id: str | None = None, limit: int = 50, cursor: str | None = None
    ) -> Page[ApiKey]:
        where = () if account_id is None else (ApiKeyRow.account_id == account_id,)
        rows, next_cursor, has_more = await self._repo.page(
            limit=limit, cursor=cursor, where=where
        )
        return Page(data=[self._dto(r) for r in rows], has_more=has_more, cursor=next_cursor)

    async def revoke(self, key_id: str) -> None:
        key = await self.get(key_id)
        if key is not None:
            await self.create(key.model_copy(update={"revoked": True}))

    async def touch(self, key_id: str, when: datetime) -> None:
        key = await self.get(key_id)
        if key is not None:
            await self.create(key.model_copy(update={"last_used_at": when}))

    async def close(self) -> None:
        return None
