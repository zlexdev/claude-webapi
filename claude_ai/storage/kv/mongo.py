"""MongoStorage: MongoDB-backed state store (optional motor dep)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorCollection

from claude_ai.storage.kv.base import BaseStorage, StorageNamespace


class MongoStorage(BaseStorage):
    def __init__(
        self,
        collection: AsyncIOMotorCollection[Any] | None = None,
        *,
        uri: str | None = None,
        db_name: str = "claude_ai",
        collection_name: str = "state",
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

    @staticmethod
    def _id(namespace: StorageNamespace | str, key: str) -> str:
        return f"{namespace}:{key}"

    async def get(self, namespace: StorageNamespace | str, key: str) -> Any | None:
        doc = await self._col.find_one({"_id": self._id(namespace, key)})
        return doc.get("value") if doc else None

    async def set(
        self, namespace: StorageNamespace | str, key: str, value: Any
    ) -> None:
        await self._col.replace_one(
            {"_id": self._id(namespace, key)},
            {
                "_id": self._id(namespace, key),
                "namespace": str(namespace),
                "key": key,
                "value": value,
            },
            upsert=True,
        )

    async def delete(self, namespace: StorageNamespace | str, key: str) -> None:
        await self._col.delete_one({"_id": self._id(namespace, key)})

    async def items(self, namespace: StorageNamespace | str) -> dict[str, Any]:
        out: dict[str, Any] = {}
        cursor = self._col.find({"namespace": str(namespace)})
        async for doc in cursor:
            out[doc["key"]] = doc.get("value")
        return out
