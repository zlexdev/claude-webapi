"""MemoryStorage: in-process state store (default; not persistent across restart)."""

from __future__ import annotations

import asyncio
from typing import Any

from claude_ai.storage.kv.base import BaseStorage, StorageNamespace


class MemoryStorage(BaseStorage):
    def __init__(self) -> None:
        self._data: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, namespace: StorageNamespace | str, key: str) -> Any | None:
        async with self._lock:
            return self._data.get(str(namespace), {}).get(key)

    async def set(
        self, namespace: StorageNamespace | str, key: str, value: Any
    ) -> None:
        async with self._lock:
            self._data.setdefault(str(namespace), {})[key] = value

    async def delete(self, namespace: StorageNamespace | str, key: str) -> None:
        async with self._lock:
            self._data.get(str(namespace), {}).pop(key, None)

    async def items(self, namespace: StorageNamespace | str) -> dict[str, Any]:
        async with self._lock:
            return dict(self._data.get(str(namespace), {}))
