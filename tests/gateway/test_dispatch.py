"""Tests for the shared adapter pipeline (run_route) — framework-free.

This is the core every server adapter calls; verifying it here covers auth, error→
envelope mapping, and SSE streaming for all three servers at once.
"""

from __future__ import annotations

from typing import Any

from gateway.servers.dispatch import run_route
from gateway.servers.handlers import GatewayHandlers
from gateway.servers.routes import ROUTES
from gateway.shared.container import AppContainer

_BY_KEY = {(r.http, r.path): r for r in ROUTES}


def route(http: str, path: str) -> Any:
    return _BY_KEY[(http, path)]


async def _call(container: AppContainer, handlers: GatewayHandlers, http: str, path: str, **kw: Any) -> Any:
    kw.setdefault("path_params", {})
    kw.setdefault("query", {})
    kw.setdefault("json_body", {})
    kw.setdefault("headers", {})
    return await run_route(container, handlers, route(http, path), **kw)


async def test_all_route_handlers_exist(handlers: GatewayHandlers) -> None:
    for r in ROUTES:
        assert callable(getattr(handlers, r.handler, None)), r.handler


async def test_admin_generate_then_key_completion(container: AppContainer, handlers: GatewayHandlers) -> None:
    gen = await _call(
        container,
        handlers,
        "POST",
        "/system/keys/generate",
        json_body={"cookies": {"sessionKey": "s"}},
        headers={"x-admin-token": "admintok"},
    )
    assert gen.status == 200 and gen.json["key"].startswith("sk-")
    raw = gen.json["key"]
    out = await _call(
        container,
        handlers,
        "POST",
        "/v1/chat/completions",
        json_body={"model": "x", "messages": [{"role": "user", "content": "hi"}]},
        headers={"authorization": f"Bearer {raw}"},
    )
    assert out.status == 200 and out.json["object"] == "chat.completion"


async def test_missing_key_maps_to_401(container: AppContainer, handlers: GatewayHandlers) -> None:
    out = await _call(
        container, handlers, "POST", "/v1/chat/completions", json_body={"model": "x", "messages": []}
    )
    assert out.status == 401
    assert out.json["error"]["type"] == "authentication_error"


async def test_admin_forbidden_maps_to_401(container: AppContainer, handlers: GatewayHandlers) -> None:
    out = await _call(
        container, handlers, "POST", "/system/keys/generate", headers={"x-admin-token": "wrong"}
    )
    assert out.status == 401


async def test_unknown_method_maps_to_400(container: AppContainer, handlers: GatewayHandlers) -> None:
    gen = await _call(
        container, handlers, "POST", "/system/keys/generate",
        json_body={"cookies": {"sessionKey": "s"}}, headers={"x-admin-token": "admintok"},
    )
    raw = gen.json["key"]
    out = await _call(
        container, handlers, "POST", "/v1/methods/invoke",
        json_body={"method": "Nope", "params": {}}, headers={"authorization": f"Bearer {raw}"},
    )
    assert out.status == 400 and out.json["error"]["type"] == "invalid_request_error"


async def test_stream_outcome(container: AppContainer, handlers: GatewayHandlers) -> None:
    gen = await _call(
        container, handlers, "POST", "/system/keys/generate",
        json_body={"cookies": {"sessionKey": "s"}}, headers={"x-admin-token": "admintok"},
    )
    raw = gen.json["key"]
    out = await _call(
        container, handlers, "POST", "/v1/chat/completions",
        json_body={"model": "x", "stream": True, "messages": [{"role": "user", "content": "hi"}]},
        headers={"authorization": f"Bearer {raw}"},
    )
    assert out.stream is not None and out.json is None
    lines = [line async for line in out.stream]
    assert lines[-1] == "data: [DONE]\n\n"
