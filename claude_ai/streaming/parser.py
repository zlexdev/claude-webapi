"""SSEParser: low-level Server-Sent-Events line/data parsing."""

import json
import logging
from typing import Any

from claude_ai.exceptions import StreamError

logger = logging.getLogger("claude_ai")


class SSEParser:
    @staticmethod
    def parse_line(line: str) -> tuple[str, str] | None:
        line = line.rstrip("\r\n")
        if not line:
            return None
        if line.startswith(":"):
            return None
        field, _, value = line.partition(":")
        if not field:
            return None
        value = value.lstrip(" ")  # single leading space is optional per SSE spec
        return (field, value)

    @staticmethod
    def parse_data(data: str) -> dict[str, Any]:
        try:
            return json.loads(data)
        except json.JSONDecodeError as exc:
            raise StreamError("unknown", data, f"Invalid JSON: {exc}") from exc

    @classmethod
    def parse_chunk(cls, text: str) -> list[tuple[str, dict[str, Any]]]:
        events: list[tuple[str, dict[str, Any]]] = []
        current_event: str | None = None
        data_lines: list[str] = []

        for line in text.splitlines():
            parsed = cls.parse_line(line)
            if parsed is None:
                if line.startswith(":"):
                    continue
                if current_event and data_lines:
                    events.append(
                        (current_event, cls.parse_data("\n".join(data_lines)))
                    )
                current_event = None
                data_lines = []
                continue

            field, value = parsed
            if field == "event":
                if current_event and data_lines:
                    events.append(
                        (current_event, cls.parse_data("\n".join(data_lines)))
                    )
                    data_lines = []
                current_event = value
            elif field == "data":
                data_lines.append(value)

        if current_event and data_lines:
            events.append((current_event, cls.parse_data("\n".join(data_lines))))

        return events
