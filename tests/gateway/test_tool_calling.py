"""Tool-calling: unit (protocol + prompt builder) + handler-level (SC-1..SC-6)."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from gateway.features.completion.schemas.openai import (
    InMessage,
    Role,
    ToolCall,
    ToolCallFunction,
    ToolDef,
    ToolFunction,
)
from gateway.features.completion.services.prompt_builder import PromptBuilder, has_tool_history
from gateway.features.completion.services.tool_protocol import (
    parse_tool_calls,
    render_tools_preamble,
    split_tools,
)
from gateway.servers.context import JsonResult, RequestContext, StreamResult
from gateway.servers.handlers import GatewayHandlers
from gateway.shared.container import AppContainer

# ----- fixtures / helpers -----------------------------------------------------

_WEATHER = ToolDef(
    function=ToolFunction(
        name="get_weather",
        description="Get the weather",
        parameters={"type": "object", "properties": {"city": {"type": "string"}}},
    )
)
_WEB_SEARCH = ToolDef(function=ToolFunction(name="web_search"))


def body(result: JsonResult) -> Any:
    return result.body.model_dump() if isinstance(result.body, BaseModel) else result.body


async def _new_key(handlers: GatewayHandlers) -> str:
    payload = {"cookies": {"sessionKey": "s"}, "name": "t"}
    result = await handlers.system_key_generate(RequestContext(json_body=payload))
    assert isinstance(result, JsonResult)
    return body(result)["key"]


async def _ctx(container: AppContainer, raw: str, **kw: Any) -> RequestContext:
    principal = await container.authenticate(f"Bearer {raw}")
    return RequestContext(principal=principal, **kw)


# ----- unit: split_tools ------------------------------------------------------


def test_split_tools_routes_native_and_custom() -> None:
    native, custom = split_tools([_WEB_SEARCH, _WEATHER], None)
    assert [n.name for n in native] == ["web_search"]
    assert native[0].as_dict() == {"type": "web_search_v0", "name": "web_search"}
    assert [c.function.name for c in custom] == ["get_weather"]


def test_split_tools_none_suppresses_custom_keeps_native() -> None:
    native, custom = split_tools([_WEB_SEARCH, _WEATHER], "none")
    assert [n.name for n in native] == ["web_search"]
    assert custom == []


def test_split_tools_empty() -> None:
    assert split_tools(None, None) == ([], [])


# ----- unit: render_tools_preamble -------------------------------------------


def test_preamble_lists_function_and_schema() -> None:
    text = render_tools_preamble([_WEATHER], None)
    assert "get_weather" in text and "Get the weather" in text
    assert "<tool_call>" in text and '"city"' in text


def test_preamble_required_and_forced_nudge() -> None:
    assert "MUST call one of the tools" in render_tools_preamble([_WEATHER], "required")
    forced = {"type": "function", "function": {"name": "get_weather"}}
    assert "MUST call the `get_weather`" in render_tools_preamble([_WEATHER], forced)


# ----- unit: parse_tool_calls -------------------------------------------------


def test_parse_single_tag() -> None:
    calls = parse_tool_calls('<tool_call>{"name": "get_weather", "arguments": {"city": "Paris"}}</tool_call>')
    assert len(calls) == 1
    assert calls[0].name == "get_weather" and calls[0].arguments == {"city": "Paris"}


def test_parse_multiple_tags() -> None:
    text = (
        '<tool_call>{"name": "a", "arguments": {}}</tool_call>\n'
        '<tool_call>{"name": "b", "arguments": {"x": 1}}</tool_call>'
    )
    assert [c.name for c in parse_tool_calls(text)] == ["a", "b"]


def test_parse_json_fence() -> None:
    calls = parse_tool_calls('here you go:\n```json\n{"name": "a", "arguments": {"x": 1}}\n```')
    assert len(calls) == 1 and calls[0].arguments == {"x": 1}


def test_parse_bare_object() -> None:
    calls = parse_tool_calls('{"name": "a", "arguments": {}}')
    assert len(calls) == 1 and calls[0].name == "a"


def test_parse_stringified_arguments() -> None:
    calls = parse_tool_calls('<tool_call>{"name": "a", "arguments": "{\\"x\\": 1}"}</tool_call>')
    assert calls[0].arguments == {"x": 1}


def test_parse_none_for_plain_text() -> None:
    assert parse_tool_calls("just a normal answer") == []
    assert parse_tool_calls("") == []
    assert parse_tool_calls('<tool_call>not json</tool_call>') == []


# ----- unit: tool-aware prompt builder ---------------------------------------


def test_flatten_renders_tool_history_once() -> None:
    msgs = [
        InMessage(role=Role.USER, content="weather in Paris?"),
        InMessage(
            role=Role.ASSISTANT,
            content=None,
            tool_calls=[
                ToolCall(id="call_1", function=ToolCallFunction(name="get_weather", arguments='{"city": "Paris"}'))
            ],
        ),
        InMessage(role=Role.TOOL, tool_call_id="call_1", content="18C sunny"),
    ]
    flat = PromptBuilder.flatten(msgs)
    assert flat.count("18C sunny") == 1
    assert "Assistant called: get_weather(" in flat
    assert "Tool result [call_1]: 18C sunny" in flat
    assert has_tool_history(msgs)


def test_has_tool_history_false_for_plain() -> None:
    assert not has_tool_history([InMessage(role=Role.USER, content="hi")])


# ----- handler-level: SC-1..SC-6 ---------------------------------------------


async def test_custom_tool_emits_tool_calls(
    container: AppContainer, handlers: GatewayHandlers
) -> None:
    container.orch.client.collect_text = (  # type: ignore[attr-defined]
        '<tool_call>{"name": "get_weather", "arguments": {"city": "Paris"}}</tool_call>'
    )
    raw = await _new_key(handlers)
    ctx = await _ctx(
        container,
        raw,
        json_body={
            "model": "x",
            "messages": [{"role": "user", "content": "weather in Paris?"}],
            "tools": [_WEATHER.model_dump()],
        },
    )
    result = await handlers.chat_completions(ctx)
    assert isinstance(result, JsonResult)
    data = body(result)
    choice = data["choices"][0]
    assert choice["finish_reason"] == "tool_calls"
    assert choice["message"]["content"] is None
    call = choice["message"]["tool_calls"][0]
    assert call["id"].startswith("call_")
    assert call["function"]["name"] == "get_weather"
    assert json.loads(call["function"]["arguments"]) == {"city": "Paris"}


async def test_follow_up_with_tool_result_answers_text(
    container: AppContainer, handlers: GatewayHandlers
) -> None:
    raw = await _new_key(handlers)
    ctx = await _ctx(
        container,
        raw,
        json_body={
            "model": "x",
            "messages": [
                {"role": "user", "content": "weather in Paris?"},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {"id": "call_1", "type": "function",
                         "function": {"name": "get_weather", "arguments": "{\"city\": \"Paris\"}"}}
                    ],
                },
                {"role": "tool", "tool_call_id": "call_1", "content": "18C sunny"},
            ],
            "tools": [_WEATHER.model_dump()],
        },
    )
    result = await handlers.chat_completions(ctx)
    assert isinstance(result, JsonResult)
    data = body(result)
    assert data["choices"][0]["finish_reason"] == "stop"
    assert data["choices"][0]["message"]["content"] == "Hello there"
    # the tool round-trip forced a full flatten — the result must be in the prompt
    assert "Tool result [call_1]: 18C sunny" in container.orch.client.recorded_prompt  # type: ignore[attr-defined]


async def test_native_web_search_pass_through(
    container: AppContainer, handlers: GatewayHandlers
) -> None:
    raw = await _new_key(handlers)
    ctx = await _ctx(
        container,
        raw,
        json_body={
            "model": "x",
            "messages": [{"role": "user", "content": "latest news"}],
            "tools": [_WEB_SEARCH.model_dump()],
        },
    )
    result = await handlers.chat_completions(ctx)
    assert isinstance(result, JsonResult)
    data = body(result)
    # native-only request → no emulation, plain text answer
    assert data["choices"][0]["finish_reason"] == "stop"
    assert container.orch.client.recorded_tools == [  # type: ignore[attr-defined]
        {"type": "web_search_v0", "name": "web_search"}
    ]


async def test_stream_custom_tool_emits_tool_calls_chunk(
    container: AppContainer, handlers: GatewayHandlers
) -> None:
    container.orch.client.collect_text = (  # type: ignore[attr-defined]
        '<tool_call>{"name": "get_weather", "arguments": {"city": "Paris"}}</tool_call>'
    )
    raw = await _new_key(handlers)
    ctx = await _ctx(
        container,
        raw,
        json_body={
            "model": "x",
            "stream": True,
            "messages": [{"role": "user", "content": "weather?"}],
            "tools": [_WEATHER.model_dump()],
        },
    )
    result = await handlers.chat_completions(ctx)
    assert isinstance(result, StreamResult)
    lines = [line async for line in result.lines]
    assert lines[-1] == "data: [DONE]\n\n"
    payloads = [json.loads(line[6:]) for line in lines if line.startswith("data: {")]
    tool_chunks = [
        c for p in payloads for c in p["choices"] if c.get("finish_reason") == "tool_calls"
    ]
    assert len(tool_chunks) == 1
    delta = tool_chunks[0]["delta"]["tool_calls"][0]
    assert delta["function"]["name"] == "get_weather"
    assert delta["index"] == 0 and delta["id"].startswith("call_")


async def test_chat_send_honours_tools(
    container: AppContainer, handlers: GatewayHandlers
) -> None:
    container.orch.client.collect_text = (  # type: ignore[attr-defined]
        '<tool_call>{"name": "get_weather", "arguments": {"city": "Rome"}}</tool_call>'
    )
    raw = await _new_key(handlers)
    ctx = await _ctx(
        container,
        raw,
        path_params={"id": "conv-1"},
        json_body={"text": "weather in Rome?", "tools": [_WEATHER.model_dump()]},
    )
    result = await handlers.chat_send(ctx)
    assert isinstance(result, JsonResult)
    data = body(result)
    assert data["choices"][0]["finish_reason"] == "tool_calls"
    assert data["choices"][0]["message"]["tool_calls"][0]["function"]["name"] == "get_weather"


async def test_malformed_tool_call_falls_back_to_text(
    container: AppContainer, handlers: GatewayHandlers
) -> None:
    container.orch.client.collect_text = "I cannot help with that."  # type: ignore[attr-defined]
    raw = await _new_key(handlers)
    ctx = await _ctx(
        container,
        raw,
        json_body={
            "model": "x",
            "messages": [{"role": "user", "content": "weather?"}],
            "tools": [_WEATHER.model_dump()],
        },
    )
    result = await handlers.chat_completions(ctx)
    assert isinstance(result, JsonResult)
    data = body(result)
    assert data["choices"][0]["finish_reason"] == "stop"
    assert data["choices"][0]["message"]["content"] == "I cannot help with that."
