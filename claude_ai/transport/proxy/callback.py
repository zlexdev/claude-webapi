"""CallbackProxy: lazy proxy resolver via sync or async callable."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable

from claude_ai.transport.proxy.base import BaseProxyTransport, ProxyConfig

ProxyResolver = Callable[
    [], ProxyConfig | str | None | Awaitable[ProxyConfig | str | None]
]


class CallbackProxy(BaseProxyTransport):
    def __init__(self, resolver: ProxyResolver) -> None:
        self._resolver = resolver

    async def get(self) -> ProxyConfig | None:
        result = self._resolver()
        if inspect.isawaitable(result):
            result = await result
        if result is None:
            return None
        return result if isinstance(result, ProxyConfig) else ProxyConfig(url=result)
