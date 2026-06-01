"""MongoCookieStorage: MongoDB-backed cookie storage (optional motor dep)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorCollection

from claude_ai.storage.cookies.base import BaseCookieStorage


class MongoCookieStorage(BaseCookieStorage):
    def __init__(
        self,
        collection: AsyncIOMotorCollection[Any] | None = None,
        *,
        uri: str | None = None,
        db_name: str = "claude_ai",
        collection_name: str = "cookies",
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

    async def load(self, account_id: str) -> dict[str, str]:
        doc = await self._col.find_one({"_id": account_id})
        return dict(doc.get("cookies", {})) if doc else {}

    async def save(self, account_id: str, cookies: dict[str, str]) -> None:
        await self._col.replace_one(
            {"_id": account_id},
            {"_id": account_id, "cookies": dict(cookies)},
            upsert=True,
        )

    async def update(self, account_id: str, cookies: dict[str, str]) -> None:
        existing = await self.load(account_id)
        existing.update(cookies)
        await self.save(account_id, existing)

    async def delete(self, account_id: str) -> None:
        await self._col.delete_one({"_id": account_id})

    async def list_accounts(self) -> list[str]:
        ids: list[str] = []
        cursor = self._col.find({}, {"_id": 1})
        async for doc in cursor:
            ids.append(doc["_id"])
        return ids
