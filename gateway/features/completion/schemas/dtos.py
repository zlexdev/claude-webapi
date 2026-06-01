"""Internal completion DTOs + the simple text endpoint shapes."""

from __future__ import annotations

from pydantic import BaseModel

from gateway.features.completion.schemas.openai import InMessage


class CompletionInput(BaseModel):
    """Normalized from an OpenAI request or /v1/prompt before hitting the service."""

    messages: list[InMessage]
    model_alias: str
    conversation_id: str | None = None
    stream: bool = False


class TextPromptRequest(BaseModel):
    text: str
    model: str | None = None
    conversation_id: str | None = None


class TextPromptResponse(BaseModel):
    text: str
    conversation_id: str | None = None
