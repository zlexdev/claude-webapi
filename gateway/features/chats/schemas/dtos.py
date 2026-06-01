"""Chat DTOs. ``role`` is a plain string (gateway shape, not the OpenAI wire enum)."""

from __future__ import annotations

from pydantic import BaseModel


class ChatSummary(BaseModel):
    id: str
    name: str
    model: str | None = None
    updated_at: str | None = None
    is_starred: bool = False


class MessageDTO(BaseModel):
    id: str
    role: str
    text: str
    index: int
    created_at: str | None = None


class CreateChatRequest(BaseModel):
    name: str | None = None
    model: str | None = None


class SendToChatRequest(BaseModel):
    text: str
    model: str | None = None
    stream: bool = False
