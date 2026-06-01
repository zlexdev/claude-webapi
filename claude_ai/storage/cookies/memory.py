"""MemoryCookieStorage: in-process cookie storage."""

from __future__ import annotations

import asyncio

from claude_ai.storage.cookies.base import BaseCookieStorage


class MemoryCookieStorage(BaseCookieStorage):
    def __init__(self, initial: dict[str, dict[str, str]] | None = None) -> None:
        self._data: dict[str, dict[str, str]] = dict(initial or {})
        self._lock = asyncio.Lock()

    async def load(self, account_id: str) -> dict[str, str]:
        async with self._lock:
            return dict(self._data.get(account_id, {}))

    async def save(self, account_id: str, cookies: dict[str, str]) -> None:
        async with self._lock:
            self._data[account_id] = dict(cookies)

    async def update(self, account_id: str, cookies: dict[str, str]) -> None:
        async with self._lock:
            existing = self._data.setdefault(account_id, {})
            existing.update(cookies)

    async def delete(self, account_id: str) -> None:
        async with self._lock:
            self._data.pop(account_id, None)

    async def list_accounts(self) -> list[str]:
        async with self._lock:
            return list(self._data.keys())
