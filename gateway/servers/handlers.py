"""GatewayHandlers: all endpoint logic, framework-agnostic.

Each method takes a normalized ``RequestContext`` and returns a ``HandlerResult``
(JSON or SSE stream). The three server adapters only translate native request/response
to/from these types — this is the single place behaviour is defined (D4), so all three
servers are behaviourally identical.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from gateway.features.auth.errors import AccountForbidden
from gateway.features.auth.schemas.dtos import (
    AccountInfo,
    CreateAccountRequest,
    GenerateKeyRequest,
    RevokeKeyRequest,
    UpdateAccountCookiesRequest,
)
from gateway.features.auth.services.account_service import resolve_tier
from gateway.features.chats.schemas.dtos import CreateChatRequest, SendToChatRequest
from gateway.features.completion.schemas.dtos import CompletionInput, TextPromptRequest
from gateway.features.completion.schemas.openai import (
    ChatCompletionChunk,
    ChatCompletionRequest,
    InMessage,
    ModelCard,
    ModelList,
    Role,
)
from gateway.features.completion.sse import DONE, sse_line
from gateway.features.methods.schemas.dtos import MethodInvokeRequest, MethodInvokeResult
from gateway.shared.container import AppContainer
from gateway.shared.principal import Principal
from gateway.shared.schemas.pagination import PageParams
from gateway.servers.context import JsonResult, RequestContext, StreamResult


def _limit(ctx: RequestContext, default: int = 50) -> int:
    raw = ctx.query.get("limit")
    value = default
    if raw is not None:
        try:
            value = int(raw)
        except ValueError:
            value = default
    return PageParams(limit=value).limit


class GatewayHandlers:
    def __init__(self, container: AppContainer) -> None:
        self._c = container

    async def chat_completions(self, ctx: RequestContext) -> JsonResult | StreamResult:
        principal = ctx.need_principal()
        req = ChatCompletionRequest.model_validate(ctx.json_body)
        conv_id = req.conversation_id or ctx.header("x-conversation-id")
        inp = CompletionInput(
            messages=req.messages,
            model_alias=req.model,
            conversation_id=conv_id,
            stream=req.stream,
        )
        if req.stream:
            return StreamResult(self._completion_sse(self._c.completion.stream(inp, principal)))
        return JsonResult(200, await self._c.completion.complete(inp, principal))

    async def models_list(self, ctx: RequestContext) -> JsonResult:
        cards = [ModelCard(id=i) for i in self._c.mapper.list_model_ids()]
        return JsonResult(200, ModelList(data=cards))

    async def prompt(self, ctx: RequestContext) -> JsonResult:
        req = TextPromptRequest.model_validate(ctx.json_body)
        resp = await self._c.completion.text(
            req.text, req.model, req.conversation_id, ctx.need_principal()
        )
        return JsonResult(200, resp)

    async def chats_list(self, ctx: RequestContext) -> JsonResult:
        page = await self._c.chats.list_chats(ctx.need_principal(), limit=_limit(ctx))
        return JsonResult(200, page)

    async def chats_create(self, ctx: RequestContext) -> JsonResult:
        req = CreateChatRequest.model_validate(ctx.json_body)
        summary = await self._c.chats.create_chat(
            ctx.need_principal(), name=req.name, model=req.model
        )
        return JsonResult(200, summary)

    async def chat_messages(self, ctx: RequestContext) -> JsonResult:
        page = await self._c.chats.messages(
            ctx.need_principal(),
            ctx.path_params["id"],
            limit=_limit(ctx),
            cursor=ctx.query.get("cursor"),
        )
        return JsonResult(200, page)

    async def chat_send(self, ctx: RequestContext) -> JsonResult | StreamResult:
        principal = ctx.need_principal()
        req = SendToChatRequest.model_validate(ctx.json_body)
        inp = CompletionInput(
            messages=[InMessage(role=Role.USER, content=req.text)],
            model_alias=req.model or self._c.settings.default_model,
            conversation_id=ctx.path_params["id"],
            stream=req.stream,
        )
        if req.stream:
            return StreamResult(self._completion_sse(self._c.completion.stream(inp, principal)))
        return JsonResult(200, await self._c.completion.complete(inp, principal))

    async def methods_list(self, ctx: RequestContext) -> JsonResult:
        return JsonResult(200, self._c.docgen.as_list())

    async def methods_invoke(self, ctx: RequestContext) -> JsonResult | StreamResult:
        principal = ctx.need_principal()
        req = MethodInvokeRequest.model_validate(ctx.json_body)
        account_id = self._resolve_account(req.account_id, principal)
        spec = self._c.registry.get(req.method)  # raises UnknownMethod (400)
        if spec.is_stream or req.stream:
            return StreamResult(self._methods_sse(req.method, account_id, req.params))
        result = await self._c.dispatch.invoke(req.method, account_id, req.params)
        return JsonResult(
            200, MethodInvokeResult(method=req.method, account_id=account_id, result=result)
        )

    async def system_account_create(self, ctx: RequestContext) -> JsonResult:
        req = CreateAccountRequest.model_validate(ctx.json_body)
        account = await self._c.account_service.provision(
            req.cookies,
            org_uuid=req.org_uuid,
            name=req.name,
            tier=resolve_tier(req.tier),
            user_agent=req.user_agent,
        )
        return JsonResult(200, {"account_id": account.account_id})

    async def system_account_list(self, ctx: RequestContext) -> JsonResult:
        page = await self._c.account_service.page(
            limit=_limit(ctx), cursor=ctx.query.get("cursor")
        )
        return JsonResult(200, page)

    async def system_account_update(self, ctx: RequestContext) -> JsonResult:
        req = UpdateAccountCookiesRequest.model_validate(ctx.json_body)
        account = await self._c.account_service.update_cookies(
            ctx.path_params["id"], req.cookies, user_agent=req.user_agent
        )
        return JsonResult(200, AccountInfo.of(account))

    async def system_key_generate(self, ctx: RequestContext) -> JsonResult:
        req = GenerateKeyRequest.model_validate(ctx.json_body)
        info, raw = await self._c.apikey_service.generate(req)
        return JsonResult(200, {"key": raw, "info": info.model_dump(mode="json")})

    async def system_key_list(self, ctx: RequestContext) -> JsonResult:
        page = await self._c.apikey_service.page(
            account_id=ctx.query.get("account_id"),
            limit=_limit(ctx),
            cursor=ctx.query.get("cursor"),
        )
        return JsonResult(200, page)

    async def system_key_revoke(self, ctx: RequestContext) -> JsonResult:
        req = RevokeKeyRequest.model_validate(ctx.json_body)
        await self._c.apikey_service.revoke(req.key_id)
        return JsonResult(200, {"revoked": req.key_id})

    async def health(self, ctx: RequestContext) -> JsonResult:
        return JsonResult(200, {"status": "ok", "server": self._c.settings.server})

    def _resolve_account(self, account_id: str | None, principal: Principal) -> str:
        if account_id and account_id != principal.account_id and not principal.is_admin:
            raise AccountForbidden()
        return account_id or principal.account_id

    async def _completion_sse(
        self, chunks: AsyncIterator[ChatCompletionChunk]
    ) -> AsyncIterator[str]:
        async for chunk in chunks:
            yield sse_line(chunk)
        yield DONE

    async def _methods_sse(
        self, method: str, account_id: str, params: dict[str, object]
    ) -> AsyncIterator[str]:
        async for event in self._c.dispatch.invoke_stream(method, account_id, params):
            yield f"data: {json.dumps(event)}\n\n"
        yield DONE
