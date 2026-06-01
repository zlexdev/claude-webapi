"""AioSqliteStorage: SQLite-backed state store (optional aiosqlite dep)."""

from __future__ import annotations

import json
from typing import Any

try:
    import aiosqlite
except ImportError:
    aiosqlite = None  # type: ignore[assignment]

from claude_ai.storage.kv.base import BaseStorage, StorageNamespace

_SCHEMA = """
CREATE TABLE IF NOT EXISTS claude_kv (
    namespace TEXT NOT NULL,
    key       TEXT NOT NULL,
    payload   TEXT NOT NULL,
    PRIMARY KEY (namespace, key)
)
"""


class AioSqliteStorage(BaseStorage):
    def __init__(self, path: str = "claude_kv.db") -> None:
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

    async def get(self, namespace: StorageNamespace | str, key: str) -> Any | None:
        conn = await self._get()
        async with conn.execute(
            "SELECT payload FROM claude_kv WHERE namespace = ? AND key = ?",
            (str(namespace), key),
        ) as cur:
            row = await cur.fetchone()
        return json.loads(row[0]) if row else None

    async def set(
        self, namespace: StorageNamespace | str, key: str, value: Any
    ) -> None:
        conn = await self._get()
        await conn.execute(
            "INSERT OR REPLACE INTO claude_kv(namespace, key, payload) "
            "VALUES(?, ?, ?)",
            (str(namespace), key, json.dumps(value)),
        )
        await conn.commit()

    async def delete(self, namespace: StorageNamespace | str, key: str) -> None:
        conn = await self._get()
        await conn.execute(
            "DELETE FROM claude_kv WHERE namespace = ? AND key = ?",
            (str(namespace), key),
        )
        await conn.commit()

    async def items(self, namespace: StorageNamespace | str) -> dict[str, Any]:
        conn = await self._get()
        async with conn.execute(
            "SELECT key, payload FROM claude_kv WHERE namespace = ?",
            (str(namespace),),
        ) as cur:
            rows = await cur.fetchall()
        return {r[0]: json.loads(r[1]) for r in rows}

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
