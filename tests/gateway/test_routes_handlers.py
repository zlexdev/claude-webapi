"""Handler-level route-contract tests — the behaviour all three servers share (D4)."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

from gateway.features.auth.errors import AccountForbidden, InvalidApiKey, RevokedApiKey
from gateway.features.methods.errors import UnknownMethod
from gateway.servers.context import JsonResult, RequestContext, StreamResult
from gateway.servers.handlers import GatewayHandlers
from gateway.shared.container import AppContainer


def body(result: JsonResult) -> Any:
    return result.body.model_dump() if isinstance(result.body, BaseModel) else result.body


async def _new_key(handlers: GatewayHandlers, **req: Any) -> str:
    payload = {"cookies": {"sessionKey": "s"}, "name": "t", **req}
    result = await handlers.system_key_generate(RequestContext(json_body=payload))
    assert isinstance(result, JsonResult)
    return result.body["key"]  # type: ignore[index]


async def _principal_ctx(container: AppContainer, raw: str, **kw: Any) -> RequestContext:
    principal = await container.authenticate(f"Bearer {raw}")
    return RequestContext(principal=principal, **kw)


async def test_health(handlers: GatewayHandlers) -> None:
    result = await handlers.health(RequestContext())
    assert isinstance(result, JsonResult)
    assert body(result)["status"] == "ok"


async def test_key_generate_and_authenticate(container: AppContainer, handlers: GatewayHandlers) -> None:
    raw = await _new_key(handlers)
    assert raw.startswith("sk-")
    principal = await container.authenticate(f"Bearer {raw}")
    assert principal.account_id.startswith("acc_")


async def test_invalid_and_revoked_key(container: AppContainer, handlers: GatewayHandlers) -> None:
    with pytest.raises(InvalidApiKey):
        await container.authenticate("Bearer sk-nope")
    raw = await _new_key(handlers)
    principal = await container.authenticate(f"Bearer {raw}")
    await handlers.system_key_revoke(RequestContext(json_body={"key_id": principal.key_id}))
    with pytest.raises(RevokedApiKey):
        await container.authenticate(f"Bearer {raw}")


async def test_chat_completions_non_stream(container: AppContainer, handlers: GatewayHandlers) -> None:
    raw = await _new_key(handlers)
    ctx = await _principal_ctx(
        container, raw, json_body={"model": "gemini-3.5-flash", "messages": [{"role": "user", "content": "hi"}]}
    )
    result = await handlers.chat_completions(ctx)
    assert isinstance(result, JsonResult)
    data = body(result)
    assert data["object"] == "chat.completion"
    assert data["choices"][0]["message"]["content"] == "Hello there"
    assert data["choices"][0]["finish_reason"] == "stop"
    assert data["usage"]["completion_tokens"] == 7


async def test_chat_completions_stream(container: AppContainer, handlers: GatewayHandlers) -> None:
    raw = await _new_key(handlers)
    ctx = await _principal_ctx(
        container,
        raw,
        json_body={"model": "x", "stream": True, "messages": [{"role": "user", "content": "hi"}]},
    )
    result = await handlers.chat_completions(ctx)
    assert isinstance(result, StreamResult)
    lines = [line async for line in result.lines]
    assert lines[-1] == "data: [DONE]\n\n"
    text = "".join(
        __import__("json").loads(line[6:])["choices"][0]["delta"].get("content", "")
        for line in lines
        if line.startswith("data: {")
    )
    assert text == "Hello there"


async def test_prompt(container: AppContainer, handlers: GatewayHandlers) -> None:
    raw = await _new_key(handlers)
    ctx = await _principal_ctx(container, raw, json_body={"text": "quick question"})
    result = await handlers.prompt(ctx)
    assert isinstance(result, JsonResult)
    assert body(result)["text"] == "Hello there"


async def test_models_list(container: AppContainer, handlers: GatewayHandlers) -> None:
    raw = await _new_key(handlers)
    ctx = await _principal_ctx(container, raw)
    result = await handlers.models_list(ctx)
    ids = {m["id"] for m in body(result)["data"]}
    assert "claude-opus-4-6" in ids and "gemini-3.5-flash" in ids


async def test_chats_list_create_messages(container: AppContainer, handlers: GatewayHandlers) -> None:
    raw = await _new_key(handlers)
    listed = body(await handlers.chats_list(await _principal_ctx(container, raw)))
    assert listed["data"][0]["id"] == "c1"
    created = body(await handlers.chats_create(await _principal_ctx(container, raw, json_body={"name": "New"})))
    assert created["name"] == "New"
    msgs = body(
        await handlers.chat_messages(
            await _principal_ctx(container, raw, path_params={"id": "c1"}, query={"limit": "1"})
        )
    )
    assert [m["index"] for m in msgs["data"]] == [0] and msgs["has_more"] and msgs["cursor"] == "1"
    assert msgs["data"][0]["role"] == "user"


async def test_methods_list_and_invoke(container: AppContainer, handlers: GatewayHandlers) -> None:
    raw = await _new_key(handlers)
    listed = body(await handlers.methods_list(await _principal_ctx(container, raw)))
    assert len(listed["data"]) > 50
    ctx = await _principal_ctx(
        container, raw, json_body={"method": "ListConversations", "params": {"limit": 5}}
    )
    result = await handlers.methods_invoke(ctx)
    assert isinstance(result, JsonResult)
    assert body(result)["result"]["method"] == "ListConversations"


async def test_methods_invoke_unknown(container: AppContainer, handlers: GatewayHandlers) -> None:
    raw = await _new_key(handlers)
    ctx = await _principal_ctx(container, raw, json_body={"method": "DoesNotExist", "params": {}})
    with pytest.raises(UnknownMethod):
        await handlers.methods_invoke(ctx)


async def test_methods_invoke_scope_forbidden(container: AppContainer, handlers: GatewayHandlers) -> None:
    raw = await _new_key(handlers)  # ACCOUNT-scope key
    ctx = await _principal_ctx(
        container, raw, json_body={"method": "ListConversations", "account_id": "acc_other", "params": {}}
    )
    with pytest.raises(AccountForbidden):
        await handlers.methods_invoke(ctx)


async def test_admin_listings(container: AppContainer, handlers: GatewayHandlers) -> None:
    await _new_key(handlers)
    accounts = body(await handlers.system_account_list(RequestContext(query={"limit": "10"})))
    assert accounts["data"] and "cookies" not in accounts["data"][0]
    keys = body(await handlers.system_key_list(RequestContext(query={"limit": "10"})))
    assert keys["data"] and "key_hash" not in keys["data"][0]


async def test_account_update_cookies_refreshes_client(
    container: AppContainer, handlers: GatewayHandlers
) -> None:
    raw = await _new_key(handlers)
    principal = await container.authenticate(f"Bearer {raw}")
    acc_id = principal.account_id
    orch: Any = container.orch

    result = await handlers.system_account_update(
        RequestContext(
            path_params={"id": acc_id},
            json_body={"cookies": {"sessionKey": "fresh", "cf_clearance": "cf2"}, "user_agent": "UA/2"},
        )
    )
    assert isinstance(result, JsonResult)
    info = body(result)
    assert info["account_id"] == acc_id and info["user_agent"] == "UA/2"
    assert "cookies" not in info  # AccountInfo never leaks the jar

    stored = await container.accounts.get(acc_id)
    assert stored is not None
    assert stored.cookies == {"sessionKey": "fresh", "cf_clearance": "cf2"}
    assert stored.user_agent == "UA/2"
    # pooled client was torn down and rebuilt with the fresh jar
    assert acc_id in orch.removed and orch.added.count(acc_id) == 2


async def test_account_update_cookies_unknown_account(handlers: GatewayHandlers) -> None:
    from gateway.features.auth.errors import AccountNotFound

    with pytest.raises(AccountNotFound):
        await handlers.system_account_update(
            RequestContext(path_params={"id": "acc_missing"}, json_body={"cookies": {"sessionKey": "x"}})
        )


async def test_admin_token_verification(container: AppContainer) -> None:
    from gateway.features.auth.errors import AdminForbidden

    container.verify_admin("admintok")  # ok
    with pytest.raises(AdminForbidden):
        container.verify_admin("wrong")
    with pytest.raises(AdminForbidden):
        container.verify_admin(None)
