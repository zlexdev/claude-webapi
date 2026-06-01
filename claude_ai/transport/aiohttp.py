"""AiohttpTransport: aiohttp-backed transport (the default).

Mirrors HttpxTransport's contract — base-url join, timeout, proxy pool with
failure reporting + bus event, JSON/content/multipart bodies, and line-wise SSE
streaming. Cookies travel in the request's ``cookie`` header (built by
``build_auth_headers``), so the session uses a ``DummyCookieJar`` to avoid aiohttp
re-managing them.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from enum import Enum
from typing import Any

import aiohttp

from claude_ai.events.proxy import ProxyInvalidEvent
from claude_ai.exceptions import NetworkError
from claude_ai.transport.base import (
    BaseTransport,
    TransportRequest,
    TransportResponse,
)
from claude_ai.transport.proxy.base import BaseProxyTransport, ProxyConfig

ProxyFailureCallback = Any


class AiohttpTransport(BaseTransport):
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
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._follow_redirects = follow_redirects
        self._proxy_pool = proxy_pool
        self._on_proxy_failure = on_proxy_failure
        self._bus = bus
        self._session: aiohttp.ClientSession | None = None

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self._timeout, cookie_jar=aiohttp.DummyCookieJar()
            )
        return self._session

    @staticmethod
    def _full_url(base: str, url: str) -> str:
        if url.startswith(("http://", "https://")):
            return url
        if base and not base.endswith("/") and not url.startswith("/"):
            return f"{base}/{url}"
        return f"{base}{url}"

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
            await self._bus.publish(ProxyInvalidEvent(proxy_url=proxy.url, reason=str(exc)))

    def _request_kwargs(self, request: TransportRequest, proxy: ProxyConfig | None) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "headers": request.headers,
            "allow_redirects": self._follow_redirects,
        }
        if proxy is not None:
            kwargs["proxy"] = proxy.url
        if request.params:
            kwargs["params"] = _coerce_query(request.params)
        if request.files is not None:
            form = aiohttp.FormData()
            for name, (filename, content, content_type) in request.files.items():
                form.add_field(name, content, filename=filename, content_type=content_type)
            kwargs["data"] = form
        elif request.json is not None:
            kwargs["json"] = request.json
        elif request.content is not None:
            kwargs["data"] = request.content
        return kwargs

    async def send(self, request: TransportRequest) -> TransportResponse:
        proxy = await self._resolve_proxy()
        session = self._get_session()
        url = self._full_url(self._base_url, request.url)
        try:
            async with session.request(request.method, url, **self._request_kwargs(request, proxy)) as resp:
                content = await resp.read()
                text = content.decode("utf-8", errors="replace")
                json_body = _safe_json(content)
                response = TransportResponse(
                    status_code=resp.status,
                    headers={k: v for k, v in resp.headers.items()},
                    content=content,
                    text=text,
                    json_body=json_body,
                )
        except aiohttp.ClientError as exc:
            if proxy is not None:
                await self._on_failure(proxy, exc)
            raise NetworkError(url, exc) from exc
        if proxy is not None and self._proxy_pool is not None:
            await self._proxy_pool.report_success(proxy)
        return response

    async def stream(self, request: TransportRequest) -> AsyncIterator[str]:
        proxy = await self._resolve_proxy()
        session = self._get_session()
        url = self._full_url(self._base_url, request.url)
        kwargs = self._request_kwargs(request, proxy)
        try:
            resp = await session.request(request.method, url, **kwargs)
        except aiohttp.ClientError as exc:
            if proxy is not None:
                await self._on_failure(proxy, exc)
            raise NetworkError(url, exc) from exc
        if proxy is not None and self._proxy_pool is not None:
            await self._proxy_pool.report_success(proxy)
        if resp.status >= 400:
            text = await resp.text()
            resp.release()
            from claude_ai.exceptions import raise_for_status

            json_body = _safe_json(text.encode())
            if isinstance(json_body, dict):
                err = json_body.get("error", {})
                msg = (err.get("message", "") if isinstance(err, dict) else str(err)) or json_body.get("detail", "") or text[:200]
            else:
                msg = text[:200]
            raise_for_status(resp.status, msg)
        return _stream_lines(resp)

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
            self._session = None


def _coerce_query(params: dict[str, Any]) -> dict[str, str | int | float]:
    # aiohttp/yarl only accept str|int|float query values (httpx also took bool/enum).
    # Match httpx: bool -> "true"/"false", Enum -> its value, drop None.
    out: dict[str, str | int | float] = {}
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, Enum):
            value = value.value
        if isinstance(value, bool):
            out[key] = "true" if value else "false"
        elif isinstance(value, (int, float, str)):
            out[key] = value
        else:
            out[key] = str(value)
    return out


def _safe_json(content: bytes) -> Any:
    import json

    try:
        return json.loads(content)
    except (ValueError, UnicodeDecodeError):
        return None


async def _stream_lines(resp: aiohttp.ClientResponse) -> AsyncIterator[str]:
    try:
        async for raw in resp.content:
            yield raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    finally:
        resp.release()
