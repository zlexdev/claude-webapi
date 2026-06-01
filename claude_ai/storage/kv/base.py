"""BaseStorage: namespaced async map of small JSON-able values, with enumeration.

Unlike `BaseCache` (no key listing) and `BaseCookieStorage` (dict[str,str] only),
this contract supports `items(namespace)` so orchestrator trackers can reload all
affinity pins / parked accounts on restart. Values must be JSON-serializable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any


class StorageNamespace(StrEnum):
    AFFINITY = "affinity"
    PARKING = "parking"


class BaseStorage(ABC):
    @abstractmethod
    async def get(self, namespace: StorageNamespace | str, key: str) -> Any | None: ...

    @abstractmethod
    async def set(
        self, namespace: StorageNamespace | str, key: str, value: Any
    ) -> None: ...

    @abstractmethod
    async def delete(self, namespace: StorageNamespace | str, key: str) -> None: ...

    @abstractmethod
    async def items(self, namespace: StorageNamespace | str) -> dict[str, Any]: ...

    async def clear(self, namespace: StorageNamespace | str) -> None:
        for key in list(await self.items(namespace)):
            await self.delete(namespace, key)

    async def close(self) -> None:
        return None
