"""BaseSession: abstract async request/stream/multipart contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from claude_ai.methods.base import BaseMethod
from claude_ai.models.streaming import StreamEvent


class BaseSession(ABC):
    account_id: str

    @abstractmethod
    async def request(
        self, method: BaseMethod[Any, Any], params: Any = None
    ) -> Any: ...

    @abstractmethod
    async def stream(
        self, method: BaseMethod[Any, Any], params: Any = None
    ) -> AsyncIterator[StreamEvent]: ...

    @abstractmethod
    async def multipart(self, method: BaseMethod[Any, Any], params: Any) -> Any: ...

    @abstractmethod
    async def open(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

    async def __aenter__(self) -> BaseSession:
        await self.open()
        return self

    async def __aexit__(
        self, exc_type: object, exc_val: object, exc_tb: object
    ) -> None:
        await self.close()
