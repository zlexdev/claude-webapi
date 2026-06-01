"""MemoryCache: in-process TTL cache."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from claude_ai.storage.cache.base import BaseCache, CacheNamespace


class MemoryCache(BaseCache):
    def __init__(self, default_ttl: float | None = None) -> None:
        self._data: dict[str, dict[str, tuple[Any, float | None]]] = {}
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()

    @staticmethod
    def _ns(namespace: CacheNamespace | str) -> str:
        return namespace.value if isinstance(namespace, CacheNamespace) else namespace

    async def get(self, namespace: CacheNamespace | str, key: str) -> Any | None:
        ns = self._ns(namespace)
        async with self._lock:
            entry = self._data.get(ns, {}).get(key)
            if entry is None:
                return None
            value, expires = entry
            if expires is not None and expires < time.monotonic():
                del self._data[ns][key]
                return None
            return value

    async def set(
        self,
        namespace: CacheNamespace | str,
        key: str,
        value: Any,
        *,
        ttl: float | None = None,
    ) -> None:
        ns = self._ns(namespace)
        effective_ttl = ttl if ttl is not None else self._default_ttl
        expires = time.monotonic() + effective_ttl if effective_ttl else None
        async with self._lock:
            self._data.setdefault(ns, {})[key] = (value, expires)

    async def delete(self, namespace: CacheNamespace | str, key: str) -> None:
        ns = self._ns(namespace)
        async with self._lock:
            self._data.get(ns, {}).pop(key, None)

    async def clear(self, namespace: CacheNamespace | str | None = None) -> None:
        async with self._lock:
            if namespace is None:
                self._data.clear()
            else:
                self._data.pop(self._ns(namespace), None)
