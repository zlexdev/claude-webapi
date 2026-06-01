"""HttpxTransport: httpx-backed transport with proxy support and failure reporting (callback + bus event)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from claude_ai.events.proxy import ProxyInvalidEvent
from claude_ai.exceptions import NetworkError
from claude_ai.transport.base import (
    BaseTransport,
    TransportRequest,
    TransportResponse,
)
from claude_ai.transport.proxy.base import BaseProxyTransport, ProxyConfig

ProxyFailureCallback = Any


class HttpxTransport(BaseTransport):
    def __init__(
        self,
        *,
        base_url: str = "",
        timeout: float = 120.0,
        follow_redirects: bool = True,
        proxy_pool: BaseProxyTransport | None = None,
        on_proxy_failure: ProxyFailureCallback | None = None,
        bus: Any = None,
    ) -> None:
        self._base_url = base_url
        self._timeout = timeout
        self._follow_redirects = follow_redirects
        self._proxy_pool = proxy_pool
        self._on_proxy_failure = on_proxy_failure
        self._bus = bus
        self._clients: dict[str | None, httpx.AsyncClient] = {}

    async def _client_for(self, proxy: ProxyConfig | None) -> httpx.AsyncClient:
        key = proxy.url if proxy else None
        client = self._clients.get(key)
        if client is None:
            kwargs: dict[str, Any] = {
                "base_url": self._base_url,
                "timeout": httpx.Timeout(self._timeout),
                "follow_redirects": self._follow_redirects,
            }
            if proxy is not None:
                kwargs["proxy"] = proxy.to_httpx()
            client = httpx.AsyncClient(**kwargs)
            self._clients[key] = client
        return client

    async def _resolve_proxy(self) -> ProxyConfig | None:
        if self._proxy_pool is None:
            return None
        return await self._proxy_pool.get()

    async def _on_failure(self, proxy: ProxyConfig, exc: Exception) -> None:
        if self._proxy_pool is not None:
            await self._proxy_pool.report_failure(proxy)
        if self._on_proxy_failure is not None:
            result = self._on_proxy_failure(proxy, exc)
            if hasattr(result, "__await__"):
                await result
        if self._bus is not None:
            await self._bus.publish(
                ProxyInvalidEvent(proxy_url=proxy.url, reason=str(exc))
            )

    def _build_request(
        self, client: httpx.AsyncClient, request: TransportRequest
    ) -> httpx.Request:
        kwargs: dict[str, Any] = {
            "method": request.method,
            "url": request.url,
            "headers": request.headers,
        }
        if request.params is not None:
            kwargs["params"] = {
                k: v for k, v in request.params.items() if v is not None
            }
        if request.json is not None:
            kwargs["json"] = request.json
        if request.content is not None:
            kwargs["content"] = request.content
        if request.files is not None:
            kwargs["files"] = request.files
        return client.build_request(**kwargs)

    async def send(self, request: TransportRequest) -> TransportResponse:
        proxy = await self._resolve_proxy()
        client = await self._client_for(proxy)
        httpx_request = self._build_request(client, request)
        try:
            response = await client.send(httpx_request)
        except (httpx.ProxyError, httpx.ConnectError) as exc:
            if proxy is not None:
                await self._on_failure(proxy, exc)
            raise NetworkError(str(httpx_request.url), exc) from exc
        except httpx.TransportError as exc:
            raise NetworkError(str(httpx_request.url), exc) from exc

        if proxy is not None and self._proxy_pool is not None:
            await self._proxy_pool.report_success(proxy)

        return TransportResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            content=response.content,
            text=response.text,
            json_body=_safe_json(response),
            raw=response,
        )

    async def stream(self, request: TransportRequest) -> AsyncIterator[str]:
        proxy = await self._resolve_proxy()
        client = await self._client_for(proxy)
        httpx_request = self._build_request(client, request)
        try:
            response = await client.send(httpx_request, stream=True)
        except (httpx.ProxyError, httpx.ConnectError) as exc:
            if proxy is not None:
                await self._on_failure(proxy, exc)
            raise NetworkError(str(httpx_request.url), exc) from exc
        if proxy is not None and self._proxy_pool is not None:
            await self._proxy_pool.report_success(proxy)
        if response.status_code >= 400:
            await response.aread()
            detail = _safe_json(response)
            await response.aclose()
            from claude_ai.exceptions import raise_for_status

            if isinstance(detail, dict):
                err = detail.get("error", {})
                msg = (
                    err.get("message", "")
                    if isinstance(err, dict)
                    else str(err)
                ) or detail.get("detail", "") or response.text[:200]
            else:
                msg = response.text[:200]
            raise_for_status(response.status_code, msg)
        return _stream_lines(response)

    async def close(self) -> None:
        for client in self._clients.values():
            await client.aclose()
        self._clients.clear()


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


async def _stream_lines(response: httpx.Response) -> AsyncIterator[str]:
    try:
        async for line in response.aiter_lines():
            yield line
    finally:
        await response.aclose()
