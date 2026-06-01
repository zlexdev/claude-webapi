"""BaseCache + CacheNamespace: namespaced async KV-cache contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any


class CacheNamespace(StrEnum):
    CONVERSATION = "conversation"
    CONVERSATION_LIST = "conversation_list"
    MESSAGE = "message"
    MESSAGE_LIST = "message_list"
    PROJECT = "project"
    PROJECT_LIST = "project_list"
    PROJECT_DOC = "project_doc"
    ORGANIZATION = "organization"
    ACCOUNT = "account"


class BaseCache(ABC):
    @abstractmethod
    async def get(self, namespace: CacheNamespace | str, key: str) -> Any | None: ...

    @abstractmethod
    async def set(
        self,
        namespace: CacheNamespace | str,
        key: str,
        value: Any,
        *,
        ttl: float | None = None,
    ) -> None: ...

    @abstractmethod
    async def delete(self, namespace: CacheNamespace | str, key: str) -> None: ...

    @abstractmethod
    async def clear(self, namespace: CacheNamespace | str | None = None) -> None: ...

    async def get_many(
        self, namespace: CacheNamespace | str, keys: list[str]
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for k in keys:
            val = await self.get(namespace, k)
            if val is not None:
                result[k] = val
        return result

    async def close(self) -> None:
        return None
