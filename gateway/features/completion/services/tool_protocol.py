"""OpenAI tool-call ↔ claude.ai text protocol (isolated).

Two coexisting paths share one OpenAI ``tools`` array:

- **Path A — native claude.ai tools.** A function whose name is in ``_NATIVE``
  (``web_search`` …) maps to a claude.ai native tool entry and is forwarded into
  ``SendMessageParams.tools``. claude.ai runs it server-side; the effect lands in
  the answer text. No emulated ``tool_calls`` are emitted for it.
- **Path B — custom function emulation.** Every other function is serialized into
  a prompt preamble that instructs the model to emit a delimited JSON tool-call.
  ``parse_tool_calls`` extracts those from the reply (tolerant of fences / bare
  JSON); the caller maps them back to OpenAI ``tool_calls``.

Tool-call *history* rendering (assistant ``tool_calls`` + ``role:"tool"`` results
folded back into the prompt) lives in ``PromptBuilder``, not here — single home,
avoids the double-render bug.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from typing import Any

from claude_ai.enums.tool import ToolType
from gateway.features.completion.schemas.openai import ToolDef

# OpenAI function name → claude.ai native tool type. Extensible (FP-3): add
# "code_interpreter"/"repl" → REPL etc. once confirmed live.
_NATIVE: dict[str, ToolType] = {
    "web_search": ToolType.WEB_SEARCH,
}


@dataclass(slots=True)
class NativeTool:
    """A claude.ai native tool entry, dumped to the SDK's ``tools`` body shape."""

    name: str
    type: ToolType

    def as_dict(self) -> dict[str, str]:
        return {"type": self.type.value, "name": self.name}


@dataclass(slots=True)
class ParsedCall:
    name: str
    arguments: dict[str, Any]


def split_tools(
    tools: list[ToolDef] | None, tool_choice: str | dict[str, Any] | None
) -> tuple[list[NativeTool], list[ToolDef]]:
    """Partition the caller's tools into (native pass-through, custom emulated).

    ``tool_choice == "none"`` disables custom emulation (no preamble → plain text)
    but still lets native tools through — they are a server-side capability toggle,
    not something the caller drives turn-by-turn.
    """
    if not tools:
        return [], []
    native: list[NativeTool] = []
    custom: list[ToolDef] = []
    suppress_custom = tool_choice == "none"
    for tool in tools:
        native_type = _NATIVE.get(tool.function.name)
        if native_type is not None:
            native.append(NativeTool(name=tool.function.name, type=native_type))
        elif not suppress_custom:
            custom.append(tool)
    return native, custom


def _forced_name(tool_choice: str | dict[str, Any] | None) -> str | None:
    if isinstance(tool_choice, dict):
        fn = tool_choice.get("function")
        if isinstance(fn, dict):
            name = fn.get("name")
            if isinstance(name, str):
                return name
    return None


def render_tools_preamble(
    custom: list[ToolDef], tool_choice: str | dict[str, Any] | None
) -> str:
    """Serialize custom functions + the emit contract into a prompt preamble."""
    lines: list[str] = [
        "You have access to the following tools. To call a tool, emit a line of the form:",
        '<tool_call>{"name": "<tool_name>", "arguments": {<json args>}}</tool_call>',
        "Emit one <tool_call> block per call (multiple allowed). Emit nothing else on "
        "those lines. If no tool is needed, answer normally.",
        "",
        "Tools:",
    ]
    for tool in custom:
        fn = tool.function
        schema = json.dumps(fn.parameters or {}, ensure_ascii=False)
        desc = f" — {fn.description}" if fn.description else ""
        lines.append(f"- {fn.name}{desc}\n  parameters (JSON Schema): {schema}")

    forced = _forced_name(tool_choice)
    if forced:
        lines.append(f"\nYou MUST call the `{forced}` tool to answer this request.")
    elif tool_choice == "required":
        lines.append("\nYou MUST call one of the tools above to answer this request.")
    return "\n".join(lines)


_TAG_RE = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)
_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _coerce(obj: Any) -> ParsedCall | None:
    if not isinstance(obj, dict):
        return None
    name = obj.get("name")
    if not isinstance(name, str) or not name:
        return None
    args = obj.get("arguments", {})
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            args = {}
    if not isinstance(args, dict):
        args = {}
    return ParsedCall(name=name, arguments=args)


def parse_tool_calls(text: str) -> list[ParsedCall]:
    """Extract tool calls from a model reply. Tolerant; empty list → text fallback.

    Order: delimited ``<tool_call>`` blocks → ```json fences → a single bare
    top-level JSON object. Non-conforming candidates are skipped.
    """
    if not text:
        return []

    calls: list[ParsedCall] = []
    for raw in _TAG_RE.findall(text):
        try:
            call = _coerce(json.loads(raw))
        except json.JSONDecodeError:
            continue
        if call is not None:
            calls.append(call)
    if calls:
        return calls

    for raw in _FENCE_RE.findall(text):
        try:
            call = _coerce(json.loads(raw))
        except json.JSONDecodeError:
            continue
        if call is not None:
            calls.append(call)
    if calls:
        return calls

    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            call = _coerce(json.loads(stripped))
        except json.JSONDecodeError:
            return []
        if call is not None:
            return [call]
    return []


def mint_tool_call_id() -> str:
    return f"call_{uuid.uuid4().hex}"
