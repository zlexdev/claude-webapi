"""CompletionService: OpenAI chat completions (stream + non-stream) and the text endpoint.

Stateless by default — the messages array is flattened to one prompt sent into a fresh
conversation (created first, so the referer header is valid — R-5). A ``conversation_id``
binds to an existing chat and sends only the trailing user turn (claude keeps context).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from claude_ai.orchestrator import ClaudeOrchestrator
from gateway.base.service import BaseService
from gateway.features.completion.errors import NoMessages
from gateway.features.completion.schemas.dtos import CompletionInput, TextPromptResponse
from gateway.features.completion.schemas.openai import (
    ChatCompletionChunk,
    ChatCompletionResponse,
    InMessage,
    Role,
)
from gateway.features.completion.services.prompt_builder import PromptBuilder
from gateway.features.completion.sse import (
    completion_id,
    finish_of_event,
    make_chunk,
    make_response,
    now_epoch,
    text_of_event,
)
from gateway.features.models_map.services.model_mapper import ModelMapper
from gateway.shared.accounts import resolve_client
from gateway.shared.principal import Principal


class CompletionService(BaseService):
    def __init__(
        self, orchestrator: ClaudeOrchestrator, mapper: ModelMapper, *, default_model: str
    ) -> None:
        self._orch = orchestrator
        self._mapper = mapper
        self._default_model = default_model

    async def _prepare(self, req: CompletionInput, client: object) -> tuple[str, str, str]:
        model = self._mapper.resolve(req.model_alias)
        if req.conversation_id:
            prompt = PromptBuilder.last_user(req.messages)
        else:
            prompt = PromptBuilder.flatten(req.messages)
        if not prompt:
            raise NoMessages()
        if req.conversation_id:
            conv_uuid = req.conversation_id
        else:
            conversation = await client.create_conversation_for_prompt(prompt)  # type: ignore[attr-defined]
            conv_uuid = conversation.uuid
        return conv_uuid, prompt, model

    async def complete(
        self, req: CompletionInput, principal: Principal
    ) -> ChatCompletionResponse:
        client = await resolve_client(self._orch, principal.account_id)
        conv_uuid, prompt, model = await self._prepare(req, client)
        result = await client.send_message_and_collect(conv_uuid, prompt, model=model)
        return make_response(
            text=result.text,
            stop_reason=result.stop_reason,
            output_tokens=result.output_tokens,
            model=req.model_alias,
            prompt=prompt,
        )

    async def stream(
        self, req: CompletionInput, principal: Principal
    ) -> AsyncIterator[ChatCompletionChunk]:
        client = await resolve_client(self._orch, principal.account_id)
        conv_uuid, prompt, model = await self._prepare(req, client)
        cid = completion_id()
        created = now_epoch()
        yield make_chunk(id_=cid, created=created, model=req.model_alias, delta={"role": "assistant"})
        finish: str | None = None
        async for event in client.send_message(conv_uuid, prompt, model=model):
            piece = text_of_event(event)
            if piece:
                yield make_chunk(
                    id_=cid, created=created, model=req.model_alias, delta={"content": piece}
                )
            event_finish = finish_of_event(event)
            if event_finish:
                finish = event_finish
        yield make_chunk(
            id_=cid,
            created=created,
            model=req.model_alias,
            delta={},
            finish_reason=finish or "stop",
        )

    async def text(
        self,
        text: str,
        model: str | None,
        conversation_id: str | None,
        principal: Principal,
    ) -> TextPromptResponse:
        client = await resolve_client(self._orch, principal.account_id)
        req = CompletionInput(
            messages=[InMessage(role=Role.USER, content=text)],
            model_alias=model or self._default_model,
            conversation_id=conversation_id,
        )
        conv_uuid, prompt, resolved = await self._prepare(req, client)
        result = await client.send_message_and_collect(conv_uuid, prompt, model=resolved)
        return TextPromptResponse(text=result.text, conversation_id=conv_uuid)
