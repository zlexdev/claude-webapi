"""BaseTransport + TransportRequest/Response: abstract HTTP transport contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TransportRequest:
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, Any] | None = None
    json: dict[str, Any] | None = None
    content: bytes | None = None
    files: dict[str, tuple[str, bytes, str]] | None = None
    stream: bool = False


@dataclass(slots=True)
class TransportResponse:
    status_code: int
    headers: dict[str, str]
    content: bytes
    text: str
    json_body: Any = None
    raw: Any = None


class BaseTransport(ABC):
    @abstractmethod
    async def send(self, request: TransportRequest) -> TransportResponse: ...

    @abstractmethod
    async def stream(self, request: TransportRequest) -> AsyncIterator[str]: ...

    async def close(self) -> None:
        return None

    async def __aenter__(self) -> BaseTransport:
        return self

    async def __aexit__(
        self, exc_type: object, exc_val: object, exc_tb: object
    ) -> None:
        await self.close()
