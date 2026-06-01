"""StaticProxy: a single fixed proxy."""

from __future__ import annotations

from claude_ai.transport.proxy.base import BaseProxyTransport, ProxyConfig


class StaticProxy(BaseProxyTransport):
    def __init__(self, proxy: ProxyConfig | str) -> None:
        self._proxy = (
            proxy if isinstance(proxy, ProxyConfig) else ProxyConfig(url=proxy)
        )

    async def get(self) -> ProxyConfig | None:
        return self._proxy
