"""High-level convenience client (ClaudeAI): chat/chat_full/chat_stream/upload_and_chat shortcuts."""

import asyncio
import uuid as _uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from claude_ai.client import ClaudeAIClient
from claude_ai.models.conversation import Conversation
from claude_ai.models.streaming import StreamEvent
from claude_ai.streaming.collector import CompletionResult


class ClaudeAI(ClaudeAIClient):
    async def chat(self, prompt: str, model: str | None = None, **kwargs: Any) -> str:
        conv = await self.create_conversation(uuid=_uuid.uuid4().hex, model=model)
        result = await self.send_message_and_collect(
            conv.uuid, prompt, model=model, **kwargs
        )
        return result.text

    async def chat_full(
        self, prompt: str, model: str | None = None, **kwargs: Any
    ) -> CompletionResult:
        conv = await self.create_conversation(uuid=_uuid.uuid4().hex, model=model)
        return await self.send_message_and_collect(
            conv.uuid, prompt, model=model, **kwargs
        )

    async def chat_stream(
        self, prompt: str, model: str | None = None, **kwargs: Any
    ) -> AsyncIterator[StreamEvent]:
        conv = await self.create_conversation(uuid=_uuid.uuid4().hex, model=model)
        return await self.send_message(conv.uuid, prompt, model=model, **kwargs)

    async def upload_and_chat(
        self,
        file_path: str | Path,
        prompt: str,
        model: str | None = None,
    ) -> CompletionResult:
        path = Path(file_path)
        content = await asyncio.to_thread(path.read_bytes)
        conv = await self.create_conversation(uuid=_uuid.uuid4().hex, model=model)
        upload = await self.upload_file(conv.uuid, content, path.name)
        return await self.send_message_and_collect(
            conv.uuid,
            prompt,
            model=model,
            files=[{"file_uuid": upload.uuid, "file_name": upload.file_name}],
        )

    async def export_conversation(self, conv_uuid: str) -> Conversation:
        return await self.get_conversation(conv_uuid, tree=True)
