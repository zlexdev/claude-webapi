"""HttpSession: httpx-backed BaseSession. Owns transport + middleware + cookie storage; parses SSE; updates LimitState; emits events to bus."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from claude_ai.bus.base import BaseEventBus
from claude_ai.config import ClaudeAISettings
from claude_ai.enums.stream import StreamEventType
from claude_ai.events.message import (
    AssistantMessageCompleteEvent,
    AssistantMessageStartedEvent,
    LimitUpdatedEvent,
    StreamChunkEvent,
)
from claude_ai.exceptions import raise_for_status
from claude_ai.methods.base import BaseMethod
from claude_ai.middleware.base import Middleware, NextHandler
from claude_ai.middleware.logging import LoggingMiddleware
from claude_ai.middleware.manager import MiddlewareManager
from claude_ai.middleware.rate_limit import RateLimitMiddleware
from claude_ai.middleware.retry import RetryMiddleware
from claude_ai.models.streaming import (
    ContentBlockDelta,
    MessageDelta,
    MessageLimit,
    MessageStart,
    StreamEvent,
    TextDelta,
    ThinkingDelta,
)
from claude_ai.session.auth import build_auth_headers, cookies_from_set_cookie
from claude_ai.session.base import BaseSession
from claude_ai.session.limits import LimitState
from claude_ai.storage.cookies.base import BaseCookieStorage
from claude_ai.storage.cookies.memory import MemoryCookieStorage
from claude_ai.streaming.handler import build_event_from_payload
from claude_ai.streaming.parser import SSEParser
from claude_ai.transport.base import (
    BaseTransport,
    TransportRequest,
    TransportResponse,
)
from claude_ai.transport.httpx import HttpxTransport


class HttpSession(BaseSession):
    def __init__(
        self,
        account_id: str = "default",
        *,
        cookies: dict[str, str] | None = None,
        cookie_storage: BaseCookieStorage | None = None,
        transport: BaseTransport | None = None,
        settings: ClaudeAISettings | None = None,
        middlewares: list[Middleware[TransportRequest, TransportResponse]]
        | None = None,
        stream_middlewares: list[Middleware[StreamEvent, None]] | None = None,
        bus: BaseEventBus | None = None,
    ) -> None:
        self.account_id = account_id
        self._settings = settings or ClaudeAISettings()
        self._cookie_storage = cookie_storage or MemoryCookieStorage()
        self._initial_cookies = dict(cookies or {})
        self._cookies: dict[str, str] = {}
        self._transport = transport or self._default_transport(bus)
        self._bus = bus
        self._opened = False
        self.http_middleware: MiddlewareManager[
            TransportRequest, TransportResponse
        ] = MiddlewareManager(scope="http")
        for mw in (
            middlewares
            if middlewares is not None
            else [
                LoggingMiddleware(),
                RateLimitMiddleware(),
                RetryMiddleware(
                    max_retries=self._settings.max_retries,
                    backoff=self._settings.retry_backoff,
                ),
            ]
        ):
            self.http_middleware.use(mw)
        self.stream_middleware: MiddlewareManager[StreamEvent, None] = MiddlewareManager(
            scope="stream"
        )
        for sm in stream_middlewares or []:
            self.stream_middleware.use(sm)
        self.limit_state = LimitState()

    def _default_transport(self, bus: BaseEventBus | None) -> BaseTransport:
        if self._settings.transport == "httpx":
            return HttpxTransport(
                base_url=self._settings.base_url, timeout=self._settings.timeout, bus=bus
            )
        from claude_ai.transport.aiohttp import AiohttpTransport

        return AiohttpTransport(
            base_url=self._settings.base_url, timeout=self._settings.timeout, bus=bus
        )

    @property
    def settings(self) -> ClaudeAISettings:
        return self._settings

    @property
    def bus(self) -> BaseEventBus | None:
        return self._bus

    @property
    def cookies(self) -> dict[str, str]:
        return dict(self._cookies)

    def use(self, middleware: Middleware[TransportRequest, TransportResponse]) -> None:
        self.http_middleware.use(middleware)

    def use_stream(self, middleware: Middleware[StreamEvent, None]) -> None:
        self.stream_middleware.use(middleware)

    async def open(self) -> None:
        if self._opened:
            return
        stored = await self._cookie_storage.load(self.account_id)
        self._cookies = {**stored, **self._initial_cookies}
        if self._initial_cookies:
            await self._cookie_storage.update(self.account_id, self._initial_cookies)
        self._opened = True

    async def close(self) -> None:
        if not self._opened:
            return
        await self._transport.close()
        self._opened = False

    def _build_transport_request(
        self,
        method: BaseMethod[Any, Any],
        params: Any,
        *,
        stream: bool = False,
        multipart: bool = False,
    ) -> TransportRequest:
        mr = method.build_request(self._settings.base_url, params)
        headers = dict(mr.headers)
        headers.update(build_auth_headers(self._cookies))
        headers.setdefault("user-agent", self._settings.user_agent)
        if stream:
            headers["accept"] = "text/event-stream"
        return TransportRequest(
            method=method.__http_method__,
            url=mr.url,
            headers=headers,
            params=mr.query if not multipart else None,
            json=mr.body if not multipart else None,
            stream=stream,
            files=method.build_multipart(params) if multipart else None,  # type: ignore[attr-defined]
        )

    async def _send(
        self, request: TransportRequest, _data: dict[str, Any]
    ) -> TransportResponse:
        response = await self._transport.send(request)
        self._absorb_set_cookie(response.headers)
        return response

    def _absorb_set_cookie(self, headers: dict[str, str]) -> None:
        new_cookies = cookies_from_set_cookie(headers)
        if not new_cookies:
            return
        self._cookies.update(new_cookies)

    async def _persist_cookies(self) -> None:
        await self._cookie_storage.save(self.account_id, self._cookies)

    async def request(self, method: BaseMethod[Any, Any], params: Any = None) -> Any:
        if not self._opened:
            await self.open()
        request = self._build_transport_request(method, params)
        chain = self.http_middleware.chain(self._send)
        response = await chain(request)
        await self._persist_cookies()
        return self._parse(method, response)

    async def stream(
        self, method: BaseMethod[Any, Any], params: Any = None
    ) -> AsyncIterator[StreamEvent]:
        if not self._opened:
            await self.open()
        request = self._build_transport_request(method, params, stream=True)
        request.method = "POST"
        await self._apply_request_middleware(request)
        line_iter = await self._transport.stream(request)
        return self._iterate_stream(
            line_iter, conv_uuid=getattr(params, "conv_uuid", "")
        )

    async def _apply_request_middleware(self, request: TransportRequest) -> None:
        async def noop_terminal(
            _req: TransportRequest, _data: dict[str, Any]
        ) -> TransportResponse:
            return TransportResponse(
                status_code=0, headers={}, content=b"", text=""
            )

        chain = self.http_middleware.chain(noop_terminal)
        await chain(request)

    async def multipart(self, method: BaseMethod[Any, Any], params: Any) -> Any:
        if not self._opened:
            await self.open()
        request = self._build_transport_request(method, params, multipart=True)
        chain = self.http_middleware.chain(self._send)
        response = await chain(request)
        await self._persist_cookies()
        return self._parse(method, response)

    def _parse(self, method: BaseMethod[Any, Any], response: TransportResponse) -> Any:
        if response.status_code >= 400:
            detail = self._extract_error(response)
            raise_for_status(response.status_code, detail)
        if method.__model__ is type(None):
            return None
        if method.__model__ is bytes:
            return response.content
        return method.parse_response(
            response.json_body if response.json_body is not None else response.text
        )

    @staticmethod
    def _extract_error(response: TransportResponse) -> str:
        body = response.json_body
        if isinstance(body, dict):
            err = body.get("error", {})
            if isinstance(err, dict):
                return err.get("message", response.text[:200])
            return str(err)[:200]
        return response.text[:200]

    async def _iterate_stream(
        self, line_iter: AsyncIterator[str], conv_uuid: str
    ) -> AsyncIterator[StreamEvent]:
        current_event: str | None = None
        data_lines: list[str] = []
        text_parts: list[str] = []
        thinking_parts: list[str] = []
        message_uuid = ""
        stop_reason: str | None = None
        output_tokens = 0

        async def emit(evt: StreamEvent) -> None:
            await self._dispatch_stream(evt, conv_uuid, message_uuid)

        async for line in line_iter:
            parsed = SSEParser.parse_line(line.rstrip("\r\n"))
            if parsed is None:
                if line.rstrip("\r\n").startswith(":"):
                    continue
                if current_event and data_lines:
                    payload = SSEParser.parse_data("\n".join(data_lines))
                    evt = build_event_from_payload(current_event, payload)
                    if isinstance(evt, MessageStart):
                        message_uuid = evt.message.uuid or evt.message.id
                        if self._bus is not None:
                            await self._bus.publish(
                                AssistantMessageStartedEvent(
                                    account_id=self.account_id,
                                    conv_uuid=conv_uuid,
                                    message_uuid=message_uuid,
                                    parent_uuid=evt.message.parent_uuid,
                                    model=evt.message.model,
                                )
                            )
                    elif isinstance(evt, ContentBlockDelta):
                        delta = evt.delta
                        if isinstance(delta, TextDelta):
                            text_parts.append(delta.text)
                        elif isinstance(delta, ThinkingDelta):
                            thinking_parts.append(delta.thinking)
                        elif isinstance(delta, dict):
                            if delta.get("type") == "text_delta":
                                text_parts.append(delta.get("text", ""))
                            elif delta.get("type") == "thinking_delta":
                                thinking_parts.append(delta.get("thinking", ""))
                    elif isinstance(evt, MessageDelta):
                        stop_reason = evt.delta.stop_reason
                        output_tokens = evt.usage.output_tokens
                    elif isinstance(evt, MessageLimit):
                        self.limit_state.update(evt.message_limit)
                        if self._bus is not None:
                            await self._bus.publish(
                                LimitUpdatedEvent(
                                    account_id=self.account_id,
                                    windows={
                                        k: v.model_dump()
                                        for k, v in evt.message_limit.windows.items()
                                    },
                                    representative_claim=evt.message_limit.representativeClaim,
                                    overage_in_use=evt.message_limit.overageInUse,
                                )
                            )

                    await emit(evt)
                    if self._bus is not None:
                        await self._bus.publish(
                            StreamChunkEvent(
                                account_id=self.account_id,
                                conv_uuid=conv_uuid,
                                event=evt,
                            )
                        )
                    yield evt

                    if (
                        evt.type == StreamEventType.MESSAGE_STOP
                        and self._bus is not None
                    ):
                        await self._bus.publish(
                            AssistantMessageCompleteEvent(
                                account_id=self.account_id,
                                conv_uuid=conv_uuid,
                                message_uuid=message_uuid,
                                text="".join(text_parts),
                                thinking="".join(thinking_parts),
                                stop_reason=stop_reason,
                                output_tokens=output_tokens,
                            )
                        )

                current_event = None
                data_lines = []
                continue

            field, value = parsed
            if field == "event":
                current_event = value
            elif field == "data" and current_event:
                data_lines.append(value)

    async def _dispatch_stream(
        self, evt: StreamEvent, conv_uuid: str, message_uuid: str
    ) -> None:
        if not len(self.stream_middleware):
            return

        async def terminal(_evt: StreamEvent, _data: dict[str, Any]) -> None:
            return None

        chain: NextHandler[StreamEvent, None] = self.stream_middleware.chain(
            terminal
        ).__call__
        await chain(evt, {"conv_uuid": conv_uuid, "message_uuid": message_uuid})
