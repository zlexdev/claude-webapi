"""Unit tests for StreamCollector — replay a real claude.ai SSE stream offline and verify aggregation."""

from collections.abc import AsyncIterator

import pytest

from claude_ai.streaming.collector import StreamCollector
from claude_ai.streaming.handler import build_event_from_payload
from claude_ai.streaming.parser import SSEParser
from claude_ai.models.streaming import StreamEvent

_REAL_STREAM = (
    "event: message_start\r\n"
    'data: {"type":"message_start","message":{"id":"chatcompl_X","type":"message",'
    '"role":"assistant","model":"","parent_uuid":"p1","uuid":"u1","content":[],'
    '"stop_reason":null,"stop_sequence":null,"trace_id":"t1","request_id":"r1"}}\r\n'
    "\r\n"
    "event: content_block_start\r\n"
    'data: {"type":"content_block_start","index":0,'
    '"content_block":{"start_timestamp":"2026-01-01T00:00:00Z","type":"thinking",'
    '"thinking":"","summaries":[],"cut_off":false,"truncated":false,'
    '"alternative_display_type":null}}\r\n'
    "\r\n"
    "event: content_block_delta\r\n"
    'data: {"type":"content_block_delta","index":0,'
    '"delta":{"type":"thinking_delta","thinking":"thinking once "}}\r\n'
    "\r\n"
    "event: content_block_delta\r\n"
    'data: {"type":"content_block_delta","index":0,'
    '"delta":{"type":"thinking_delta","thinking":"and twice"}}\r\n'
    "\r\n"
    "event: content_block_stop\r\n"
    'data: {"type":"content_block_stop","index":0}\r\n'
    "\r\n"
    "event: content_block_start\r\n"
    'data: {"type":"content_block_start","index":1,'
    '"content_block":{"type":"text","text":"","citations":[]}}\r\n'
    "\r\n"
    "event: content_block_delta\r\n"
    'data: {"type":"content_block_delta","index":1,'
    '"delta":{"type":"text_delta","text":"Hello "}}\r\n'
    "\r\n"
    "event: content_block_delta\r\n"
    'data: {"type":"content_block_delta","index":1,'
    '"delta":{"type":"text_delta","text":"world"}}\r\n'
    "\r\n"
    "event: content_block_stop\r\n"
    'data: {"type":"content_block_stop","index":1}\r\n'
    "\r\n"
    "event: message_delta\r\n"
    'data: {"type":"message_delta","delta":{"stop_reason":"end_turn",'
    '"stop_sequence":null},"usage":{"output_tokens":42}}\r\n'
    "\r\n"
    "event: message_stop\r\n"
    'data: {"type":"message_stop"}\r\n'
    "\r\n"
)


async def _replay() -> AsyncIterator[StreamEvent]:
    for evt_type, payload in SSEParser.parse_chunk(_REAL_STREAM):
        yield build_event_from_payload(evt_type, payload)


@pytest.mark.asyncio
async def test_collector_aggregates_text_thinking_and_metadata() -> None:
    result = await StreamCollector(_replay()).collect()
    assert result.text == "Hello world"
    assert result.thinking == "thinking once and twice"
    assert result.message_uuid == "u1"
    assert result.parent_uuid == "p1"
    assert result.request_id == "r1"
    assert result.trace_id == "t1"
    assert result.stop_reason == "end_turn"
    assert result.output_tokens == 42
