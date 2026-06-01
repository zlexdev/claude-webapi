"""Unit tests for SSEParser — line/data/chunk parsing and edge cases."""

import pytest

from claude_ai.exceptions import StreamError
from claude_ai.streaming.parser import SSEParser


class TestParseLine:
    def test_event_line(self) -> None:
        assert SSEParser.parse_line("event: message_start") == (
            "event",
            "message_start",
        )

    def test_data_line(self) -> None:
        assert SSEParser.parse_line('data: {"k":1}') == ("data", '{"k":1}')

    def test_data_with_no_space(self) -> None:
        assert SSEParser.parse_line("data:foo") == ("data", "foo")

    def test_empty_line(self) -> None:
        assert SSEParser.parse_line("") is None

    def test_comment_line(self) -> None:
        assert SSEParser.parse_line(": keep-alive") is None

    def test_strips_crlf(self) -> None:
        assert SSEParser.parse_line("event: ping\r\n") == ("event", "ping")


class TestParseData:
    def test_valid_json(self) -> None:
        assert SSEParser.parse_data('{"a":1,"b":[2]}') == {"a": 1, "b": [2]}

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(StreamError):
            SSEParser.parse_data("{not json")


class TestParseChunk:
    def test_single_event(self) -> None:
        text = "event: ping\ndata: {}\n\n"
        events = SSEParser.parse_chunk(text)
        assert events == [("ping", {})]

    def test_multiple_events(self) -> None:
        text = (
            "event: a\ndata: {\"v\":1}\n\n"
            "event: b\ndata: {\"v\":2}\n\n"
        )
        events = SSEParser.parse_chunk(text)
        assert events == [("a", {"v": 1}), ("b", {"v": 2})]

    def test_multiline_data_concatenated(self) -> None:
        text = "event: x\ndata: {\"a\":\ndata: 1}\n\n"
        events = SSEParser.parse_chunk(text)
        assert events == [("x", {"a": 1})]

    def test_event_without_terminator_still_emitted(self) -> None:
        text = "event: tail\ndata: {\"t\":true}\n"
        events = SSEParser.parse_chunk(text)
        assert events == [("tail", {"t": True})]

    def test_comment_lines_skipped(self) -> None:
        text = ": ka\nevent: x\n: ka2\ndata: {\"v\":1}\n\n"
        events = SSEParser.parse_chunk(text)
        assert events == [("x", {"v": 1})]
