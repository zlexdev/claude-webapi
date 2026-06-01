"""BaseProxyTransport + ProxyConfig: abstract proxy resolver with success/failure feedback."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ProxyConfig:
    url: str
    username: str | None = None
    password: str | None = None

    def to_httpx(self) -> str:
        if self.username and self.password:
            scheme, sep, rest = self.url.partition("://")
            return f"{scheme}{sep}{self.username}:{self.password}@{rest}"
        return self.url


class BaseProxyTransport(ABC):
    @abstractmethod
    async def get(self) -> ProxyConfig | None: ...

    async def report_failure(self, proxy: ProxyConfig) -> None:
        return None

    async def report_success(self, proxy: ProxyConfig) -> None:
        return None
