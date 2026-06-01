"""Unit tests for the framework-free building blocks."""

from __future__ import annotations

import pytest

from gateway.features.auth.cookies_parse import parse_cookies
from gateway.features.auth.errors import CookieParseError
from gateway.features.auth.keys import KEY_PREFIX, generate_key, hash_key, verify
from gateway.features.completion.schemas.openai import InMessage, Role
from gateway.features.completion.services.prompt_builder import PromptBuilder
from gateway.features.methods.registry import MethodRegistry
from gateway.features.methods.schemas.dtos import MethodStyle
from gateway.features.models_map.services.model_mapper import ModelMapper
from gateway.shared.schemas.pagination import decode_cursor, encode_cursor


def test_keys_roundtrip() -> None:
    raw, h = generate_key()
    assert raw.startswith(KEY_PREFIX)
    assert verify(raw, h)
    assert not verify("sk-wrong", h)
    assert hash_key(raw) == h


@pytest.mark.parametrize(
    "value,expected",
    [
        ({"a": "1"}, {"a": "1"}),
        ([{"name": "k", "value": "v"}], {"k": "v"}),
        ('{"k": "v"}', {"k": "v"}),
        (".x\tTRUE\t/\tTRUE\t0\tsessionKey\tsk\n", {"sessionKey": "sk"}),
    ],
)
def test_parse_cookies(value: object, expected: dict[str, str]) -> None:
    assert parse_cookies(value) == expected  # type: ignore[arg-type]


def test_parse_cookies_rejects_garbage() -> None:
    with pytest.raises(CookieParseError):
        parse_cookies("not cookies at all")


def test_prompt_builder_flatten_and_last_user() -> None:
    msgs = [
        InMessage(role=Role.SYSTEM, content="be nice"),
        InMessage(role=Role.USER, content="first"),
        InMessage(role=Role.ASSISTANT, content="ok"),
        InMessage(role=Role.USER, content="second"),
    ]
    flat = PromptBuilder.flatten(msgs)
    assert "System: be nice" in flat and "User: second" in flat
    assert PromptBuilder.last_user(msgs) == "second"


def test_prompt_builder_multimodal_content() -> None:
    msgs = [InMessage(role=Role.USER, content=[{"type": "text", "text": "hello"}])]
    assert PromptBuilder.last_user(msgs) == "hello"


def test_model_mapper() -> None:
    mapper = ModelMapper(default_model="claude-sonnet-4-6")
    assert mapper.resolve("gemini-3.5-flash") == "claude-haiku-4-5"
    assert mapper.resolve("claude-opus-4-6") == "claude-opus-4-6"
    assert mapper.resolve("unknown-xyz") == "claude-sonnet-4-6"
    assert "gemini-3.5-flash" in mapper.list_model_ids()


def test_cursor_roundtrip() -> None:
    from datetime import UTC, datetime

    now = datetime(2026, 1, 1, tzinfo=UTC)
    cursor = encode_cursor(now, "id-1")
    ts, id_ = decode_cursor(cursor)
    assert id_ == "id-1" and ts.startswith("2026-01-01")
    with pytest.raises(ValueError):
        decode_cursor("!!!not-base64!!!")


def test_method_registry_discovers_both_styles() -> None:
    registry = MethodRegistry()
    specs = {s.name: s for s in registry.all_specs()}
    assert len(specs) > 50
    assert specs["ListConversations"].style is MethodStyle.LEGACY
    field_specs = [s for s in specs.values() if s.style is MethodStyle.FIELD]
    assert field_specs
    method, params = registry.build_instance("ListConversations", {"limit": 3}, org_uuid="o")
    assert params is not None and params.org_uuid == "o" and params.limit == 3
