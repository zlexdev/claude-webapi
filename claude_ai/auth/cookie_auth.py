"""CookieAuth: BaseAuth backed by a BaseCookieStorage with auto XSRF extraction."""

from __future__ import annotations

from claude_ai.auth.base import AuthSnapshot, BaseAuth
from claude_ai.session.auth import build_auth_headers, extract_xsrf
from claude_ai.storage.cookies.base import BaseCookieStorage
from claude_ai.storage.cookies.memory import MemoryCookieStorage


class CookieAuth(BaseAuth):
    def __init__(
        self,
        account_id: str = "default",
        *,
        cookies: dict[str, str] | None = None,
        storage: BaseCookieStorage | None = None,
    ) -> None:
        super().__init__()
        self.account_id = account_id
        self._storage = storage or MemoryCookieStorage()
        self._cookies: dict[str, str] = dict(cookies or {})
        self._headers: dict[str, str] = {}
        self._revision = 0
        self._loaded = False

    async def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        stored = await self._storage.load(self.account_id)
        merged = {**stored, **self._cookies}
        if self._cookies:
            await self._storage.save(self.account_id, merged)
        self._cookies = merged
        self._loaded = True

    async def actually(self) -> AuthSnapshot:
        async with self._lock:
            await self._ensure_loaded()
            return self._snapshot()

    def _snapshot(self) -> AuthSnapshot:
        merged_headers = dict(self._headers)
        merged_headers.update(build_auth_headers(self._cookies))
        return AuthSnapshot(
            cookies=dict(self._cookies),
            headers=merged_headers,
            xsrf_token=extract_xsrf(self._cookies),
            revision=self._revision,
        )

    async def update(
        self,
        cookies: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> AuthSnapshot:
        async with self._lock:
            await self._ensure_loaded()
            changed = False
            if cookies:
                self._cookies.update(cookies)
                await self._storage.save(self.account_id, self._cookies)
                changed = True
            if headers:
                self._headers.update(headers)
                changed = True
            if changed:
                self._revision += 1
            snapshot = self._snapshot()
        await self._notify(snapshot)
        return snapshot
