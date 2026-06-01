"""MongoCache: MongoDB-backed namespaced cache (optional motor dep)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorCollection

from claude_ai.storage.cache.base import BaseCache, CacheNamespace


class MongoCache(BaseCache):
    def __init__(
        self,
        collection: AsyncIOMotorCollection[Any] | None = None,
        *,
        uri: str | None = None,
        db_name: str = "claude_ai",
        collection_name: str = "cache",
        default_ttl: float | None = None,
    ) -> None:
        if collection is None:
            try:
                from motor.motor_asyncio import AsyncIOMotorClient
            except ImportError as exc:
                raise RuntimeError("motor is not installed; pip install motor") from exc
            if uri is None:
                raise ValueError("Either collection or uri must be provided")
            client: Any = AsyncIOMotorClient(uri)
            collection = client[db_name][collection_name]
        self._col = collection
        self._default_ttl = default_ttl

    @staticmethod
    def _ns(namespace: CacheNamespace | str) -> str:
        return namespace.value if isinstance(namespace, CacheNamespace) else namespace

    @staticmethod
    def _doc_id(ns: str, key: str) -> str:
        return f"{ns}:{key}"

    async def get(self, namespace: CacheNamespace | str, key: str) -> Any | None:
        ns = self._ns(namespace)
        doc = await self._col.find_one({"_id": self._doc_id(ns, key)})
        if doc is None:
            return None
        expires = doc.get("expires")
        if expires is not None and expires < time.time():
            await self.delete(namespace, key)
            return None
        return doc.get("value")

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
        expires = time.time() + effective_ttl if effective_ttl else None
        await self._col.replace_one(
            {"_id": self._doc_id(ns, key)},
            {
                "_id": self._doc_id(ns, key),
                "namespace": ns,
                "key": key,
                "value": value,
                "expires": expires,
            },
            upsert=True,
        )

    async def delete(self, namespace: CacheNamespace | str, key: str) -> None:
        await self._col.delete_one({"_id": self._doc_id(self._ns(namespace), key)})

    async def clear(self, namespace: CacheNamespace | str | None = None) -> None:
        if namespace is None:
            await self._col.delete_many({})
        else:
            await self._col.delete_many({"namespace": self._ns(namespace)})
