"""AioSqliteCache: SQLite-backed namespaced cache (optional aiosqlite dep)."""

from __future__ import annotations

import json
import time
from typing import Any

try:
    import aiosqlite
except ImportError:
    aiosqlite = None  # type: ignore[assignment]

from claude_ai.storage.cache.base import BaseCache, CacheNamespace

_SCHEMA = """
CREATE TABLE IF NOT EXISTS claude_cache (
    namespace TEXT NOT NULL,
    key       TEXT NOT NULL,
    payload   TEXT NOT NULL,
    expires   REAL,
    PRIMARY KEY (namespace, key)
)
"""


class AioSqliteCache(BaseCache):
    def __init__(
        self, path: str = "claude_cache.db", *, default_ttl: float | None = None
    ) -> None:
        if aiosqlite is None:
            raise RuntimeError("aiosqlite is not installed; pip install aiosqlite")
        self._path = path
        self._default_ttl = default_ttl
        self._conn: aiosqlite.Connection | None = None

    async def _get_conn(self) -> "aiosqlite.Connection":
        if self._conn is None:
            self._conn = await aiosqlite.connect(self._path)
            await self._conn.execute(_SCHEMA)
            await self._conn.commit()
        return self._conn

    @staticmethod
    def _ns(namespace: CacheNamespace | str) -> str:
        return namespace.value if isinstance(namespace, CacheNamespace) else namespace

    async def get(self, namespace: CacheNamespace | str, key: str) -> Any | None:
        conn = await self._get_conn()
        async with conn.execute(
            "SELECT payload, expires FROM claude_cache WHERE namespace=? AND key=?",
            (self._ns(namespace), key),
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        payload, expires = row
        if expires is not None and expires < time.time():
            await self.delete(namespace, key)
            return None
        return json.loads(payload)

    async def set(
        self,
        namespace: CacheNamespace | str,
        key: str,
        value: Any,
        *,
        ttl: float | None = None,
    ) -> None:
        conn = await self._get_conn()
        effective_ttl = ttl if ttl is not None else self._default_ttl
        expires = time.time() + effective_ttl if effective_ttl else None
        await conn.execute(
            "INSERT OR REPLACE INTO claude_cache(namespace, key, payload, expires) VALUES(?,?,?,?)",
            (self._ns(namespace), key, json.dumps(value), expires),
        )
        await conn.commit()

    async def delete(self, namespace: CacheNamespace | str, key: str) -> None:
        conn = await self._get_conn()
        await conn.execute(
            "DELETE FROM claude_cache WHERE namespace=? AND key=?",
            (self._ns(namespace), key),
        )
        await conn.commit()

    async def clear(self, namespace: CacheNamespace | str | None = None) -> None:
        conn = await self._get_conn()
        if namespace is None:
            await conn.execute("DELETE FROM claude_cache")
        else:
            await conn.execute(
                "DELETE FROM claude_cache WHERE namespace=?", (self._ns(namespace),)
            )
        await conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
