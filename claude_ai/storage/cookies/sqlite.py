"""AioSqliteCookieStorage: SQLite-backed cookie storage (optional aiosqlite dep)."""

from __future__ import annotations

import json

try:
    import aiosqlite
except ImportError:
    aiosqlite = None  # type: ignore[assignment]

from claude_ai.storage.cookies.base import BaseCookieStorage

_SCHEMA = """
CREATE TABLE IF NOT EXISTS claude_cookies (
    account_id TEXT PRIMARY KEY,
    payload    TEXT NOT NULL
)
"""


class AioSqliteCookieStorage(BaseCookieStorage):
    def __init__(self, path: str = "claude_cookies.db") -> None:
        if aiosqlite is None:
            raise RuntimeError("aiosqlite is not installed; pip install aiosqlite")
        self._path = path
        self._conn: aiosqlite.Connection | None = None

    async def _get(self) -> "aiosqlite.Connection":
        if self._conn is None:
            self._conn = await aiosqlite.connect(self._path)
            await self._conn.execute(_SCHEMA)
            await self._conn.commit()
        return self._conn

    async def load(self, account_id: str) -> dict[str, str]:
        conn = await self._get()
        async with conn.execute(
            "SELECT payload FROM claude_cookies WHERE account_id = ?", (account_id,)
        ) as cur:
            row = await cur.fetchone()
        return json.loads(row[0]) if row else {}

    async def save(self, account_id: str, cookies: dict[str, str]) -> None:
        conn = await self._get()
        await conn.execute(
            "INSERT OR REPLACE INTO claude_cookies(account_id, payload) VALUES(?, ?)",
            (account_id, json.dumps(cookies)),
        )
        await conn.commit()

    async def update(self, account_id: str, cookies: dict[str, str]) -> None:
        existing = await self.load(account_id)
        existing.update(cookies)
        await self.save(account_id, existing)

    async def delete(self, account_id: str) -> None:
        conn = await self._get()
        await conn.execute(
            "DELETE FROM claude_cookies WHERE account_id = ?", (account_id,)
        )
        await conn.commit()

    async def list_accounts(self) -> list[str]:
        conn = await self._get()
        async with conn.execute("SELECT account_id FROM claude_cookies") as cur:
            rows = await cur.fetchall()
        return [r[0] for r in rows]

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
