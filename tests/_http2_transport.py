"""HttpxTransport variant that uses HTTP/2 (matches real claude.ai web client)."""

from __future__ import annotations

from typing import Any

import httpx

from claude_ai.transport.httpx import HttpxTransport
from claude_ai.transport.proxy.base import ProxyConfig


class Http2HttpxTransport(HttpxTransport):
    async def _client_for(self, proxy: ProxyConfig | None) -> httpx.AsyncClient:
        key = proxy.url if proxy else None
        client = self._clients.get(key)
        if client is None:
            kwargs: dict[str, Any] = {
                "base_url": self._base_url,
                "timeout": httpx.Timeout(self._timeout),
                "follow_redirects": self._follow_redirects,
                "http2": True,
            }
            if proxy is not None:
                kwargs["proxy"] = proxy.to_httpx()
            client = httpx.AsyncClient(**kwargs)
            self._clients[key] = client
        return client
