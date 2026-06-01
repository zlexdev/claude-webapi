"""BaseApiKeyStore / BaseAccountStore — the new auth storage protocol.

Mirrors the SDK storage-family shape (ABC + swappable backends, async everywhere).
Every array read is cursor-paginated (``page``) or a bulk cursor scan (``iterate_all``)
— there is no unbounded list method, by design.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime

from gateway.features.auth.schemas.dtos import Account, ApiKey
from gateway.shared.schemas.pagination import Page


class BaseApiKeyStore(ABC):
    @abstractmethod
    async def create(self, key: ApiKey) -> None: ...

    @abstractmethod
    async def get(self, key_id: str) -> ApiKey | None: ...

    @abstractmethod
    async def get_by_hash(self, key_hash: str) -> ApiKey | None: ...

    @abstractmethod
    async def page(
        self, *, account_id: str | None = None, limit: int = 50, cursor: str | None = None
    ) -> Page[ApiKey]: ...

    @abstractmethod
    async def revoke(self, key_id: str) -> None: ...

    @abstractmethod
    async def touch(self, key_id: str, when: datetime) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...


class BaseAccountStore(ABC):
    @abstractmethod
    async def upsert(self, account: Account) -> None: ...

    @abstractmethod
    async def get(self, account_id: str) -> Account | None: ...

    @abstractmethod
    async def page(
        self, *, include_revoked: bool = False, limit: int = 50, cursor: str | None = None
    ) -> Page[Account]: ...

    @abstractmethod
    def iterate_all(self, *, include_revoked: bool = False) -> AsyncIterator[Account]: ...

    @abstractmethod
    async def revoke(self, account_id: str) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...
