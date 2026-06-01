"""ListProxy: rotating proxy list with failure-skip threshold."""

from __future__ import annotations

import asyncio
import itertools
from collections.abc import Iterable

from claude_ai.transport.proxy.base import BaseProxyTransport, ProxyConfig


class ListProxy(BaseProxyTransport):
    def __init__(
        self,
        proxies: Iterable[ProxyConfig | str],
        *,
        skip_failed_count: int = 5,
    ) -> None:
        self._proxies: list[ProxyConfig] = [
            p if isinstance(p, ProxyConfig) else ProxyConfig(url=p) for p in proxies
        ]
        if not self._proxies:
            raise ValueError("ListProxy requires at least one proxy")
        self._cycle = itertools.cycle(self._proxies)
        self._failures: dict[str, int] = {}
        self._skip_failed_count = skip_failed_count
        self._lock = asyncio.Lock()

    async def get(self) -> ProxyConfig | None:
        async with self._lock:
            for _ in range(len(self._proxies)):
                candidate = next(self._cycle)
                if self._failures.get(candidate.url, 0) < self._skip_failed_count:
                    return candidate
            self._failures.clear()
            return next(self._cycle)

    async def report_failure(self, proxy: ProxyConfig) -> None:
        async with self._lock:
            self._failures[proxy.url] = self._failures.get(proxy.url, 0) + 1

    async def report_success(self, proxy: ProxyConfig) -> None:
        async with self._lock:
            self._failures.pop(proxy.url, None)
