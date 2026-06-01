"""BaseCookieStorage: async load/save/update/delete cookies keyed by account_id."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseCookieStorage(ABC):
    @abstractmethod
    async def load(self, account_id: str) -> dict[str, str]: ...

    @abstractmethod
    async def save(self, account_id: str, cookies: dict[str, str]) -> None: ...

    @abstractmethod
    async def update(self, account_id: str, cookies: dict[str, str]) -> None: ...

    @abstractmethod
    async def delete(self, account_id: str) -> None: ...

    @abstractmethod
    async def list_accounts(self) -> list[str]: ...

    async def close(self) -> None:
        return None
