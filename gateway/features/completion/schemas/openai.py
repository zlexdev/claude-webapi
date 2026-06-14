"""OpenAI wire DTOs — the stable public contract (PUBLIC).

Text + thinking flow through; ``tools``/``tool_choice`` are honoured (native
claude.ai tools are passed through, custom functions are emulated — see
``services/tool_protocol.py``). ``temperature`` and other unknown fields are still
accepted-and-ignored. Response/chunk shapes match the ``openai`` Python SDK.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolFunction(BaseModel):
    name: str
    description: str | None = None
    parameters: dict[str, Any] | None = None  # JSON Schema (open by contract)


class ToolDef(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: Literal["function"] = "function"
    function: ToolFunction


class ToolCallFunction(BaseModel):
    name: str
    arguments: str  # JSON string (OpenAI contract)


class ToolCall(BaseModel):
    id: str
    type: Literal["function"] = "function"
    function: ToolCallFunction


class InMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    role: Role
    content: str | list[dict[str, Any]] | None = None  # tool/assistant turns may omit
    name: str | None = None
    tool_call_id: str | None = None  # role:"tool" — which call this answers
    tool_calls: list[ToolCall] | None = None  # prior assistant tool calls


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    model: str
    messages: list[InMessage]
    stream: bool = False
    temperature: float | None = None  # accepted, ignored
    conversation_id: str | None = None  # extra: bind to an existing chat (D8)
    tools: list[ToolDef] | None = None
    tool_choice: str | dict[str, Any] | None = None  # auto | none | required | {function}


class OutMessage(BaseModel):
    role: Role = Role.ASSISTANT
    content: str | None = None
    tool_calls: list[ToolCall] | None = None


class ChatChoice(BaseModel):
    index: int = 0
    message: OutMessage
    finish_reason: str | None = "stop"


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: list[ChatChoice]
    usage: Usage


class ChunkChoice(BaseModel):
    index: int = 0
    delta: dict[str, Any]
    finish_reason: str | None = None


class ChatCompletionChunk(BaseModel):
    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int
    model: str
    choices: list[ChunkChoice]


class ModelCard(BaseModel):
    id: str
    object: Literal["model"] = "model"
    created: int = 0
    owned_by: str = "claude-gateway"


class ModelList(BaseModel):
    object: Literal["list"] = "list"
    data: list[ModelCard]


class OpenAIError(BaseModel):
    message: str
    type: str
    code: str | None = None
    param: str | None = None


class OpenAIErrorEnvelope(BaseModel):
    error: OpenAIError
