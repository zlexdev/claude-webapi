"""CompletionService: OpenAI chat completions (stream + non-stream) and the text endpoint.

Stateless by default — the messages array is flattened to one prompt sent into a fresh
conversation (created first, so the referer header is valid — R-5). A ``conversation_id``
binds to an existing chat and sends only the trailing user turn (claude keeps context),
unless the messages carry a tool round-trip — then we force a full flatten so the
call→result linkage survives (SC-2).

Tools (D1–D11): native claude.ai tools (web_search …) are forwarded into the SDK's
``tools=`` (Path A); custom JSON-schema functions are emulated via a prompt preamble +
reply parsing (Path B). In custom-tool mode ``stream`` BUFFERS — it can't retract text
it already streamed — then emits one consolidated ``tool_calls`` chunk (R-1/D3).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

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
from gateway.features.completion.services.prompt_builder import PromptBuilder, has_tool_history
from gateway.features.completion.services.tool_protocol import (
    NativeTool,
    parse_tool_calls,
    render_tools_preamble,
    split_tools,
)
from gateway.features.completion.sse import (
    completion_id,
    finish_of_event,
    make_chunk,
    make_response,
    make_tool_response,
    now_epoch,
    text_of_event,
    tool_calls_chunk,
)
from gateway.features.models_map.services.model_mapper import ModelMapper
from gateway.shared.accounts import resolve_client
from gateway.shared.principal import Principal


@dataclass(slots=True)
class _Prepared:
    conv_uuid: str
    prompt: str
    model: str
    native: list[NativeTool]
    has_custom: bool


class CompletionService(BaseService):
    def __init__(
        self, orchestrator: ClaudeOrchestrator, mapper: ModelMapper, *, default_model: str
    ) -> None:
        self._orch = orchestrator
        self._mapper = mapper
        self._default_model = default_model

    async def _prepare(self, req: CompletionInput, client: object) -> _Prepared:
        model = self._mapper.resolve(req.model_alias)
        native, custom = split_tools(req.tools, req.tool_choice)
        tool_round_trip = has_tool_history(req.messages)
        if req.conversation_id and not tool_round_trip:
            prompt = PromptBuilder.last_user(req.messages)
        else:
            prompt = PromptBuilder.flatten(req.messages)
        if not prompt:
            raise NoMessages()
        if custom:
            prompt = f"{prompt}\n\n{render_tools_preamble(custom, req.tool_choice)}"
        if req.conversation_id:
            conv_uuid = req.conversation_id
        else:
            conversation = await client.create_conversation_for_prompt(prompt)  # type: ignore[attr-defined]
            conv_uuid = conversation.uuid
        return _Prepared(conv_uuid, prompt, model, native, bool(custom))

    @staticmethod
    def _native_dicts(prep: _Prepared) -> list[dict[str, str]]:
        return [n.as_dict() for n in prep.native]

    async def complete(
        self, req: CompletionInput, principal: Principal
    ) -> ChatCompletionResponse:
        client = await resolve_client(self._orch, principal.account_id)
        prep = await self._prepare(req, client)
        result = await client.send_message_and_collect(
            prep.conv_uuid, prep.prompt, model=prep.model, tools=self._native_dicts(prep)
        )
        if prep.has_custom:
            calls = parse_tool_calls(result.text)
            if calls:
                return make_tool_response(
                    calls=calls,
                    model=req.model_alias,
                    prompt=prep.prompt,
                    output_tokens=result.output_tokens,
                )
        return make_response(
            text=result.text,
            stop_reason=result.stop_reason,
            output_tokens=result.output_tokens,
            model=req.model_alias,
            prompt=prep.prompt,
        )

    async def stream(
        self, req: CompletionInput, principal: Principal
    ) -> AsyncIterator[ChatCompletionChunk]:
        client = await resolve_client(self._orch, principal.account_id)
        prep = await self._prepare(req, client)
        cid = completion_id()
        created = now_epoch()

        if prep.has_custom:
            # Buffer: emulated tool calls can't be retracted once streamed (R-1/D3).
            result = await client.send_message_and_collect(
                prep.conv_uuid, prep.prompt, model=prep.model, tools=self._native_dicts(prep)
            )
            yield make_chunk(
                id_=cid, created=created, model=req.model_alias, delta={"role": "assistant"}
            )
            calls = parse_tool_calls(result.text)
            if calls:
                yield tool_calls_chunk(
                    id_=cid, created=created, model=req.model_alias, calls=calls
                )
                return
            if result.text:
                yield make_chunk(
                    id_=cid, created=created, model=req.model_alias, delta={"content": result.text}
                )
            yield make_chunk(
                id_=cid,
                created=created,
                model=req.model_alias,
                delta={},
                finish_reason="stop",
            )
            return

        yield make_chunk(id_=cid, created=created, model=req.model_alias, delta={"role": "assistant"})
        finish: str | None = None
        # send_message is a coroutine returning the event iterator — await before async-for.
        stream = await client.send_message(
            prep.conv_uuid, prep.prompt, model=prep.model, tools=self._native_dicts(prep)
        )
        async for event in stream:
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
        prep = await self._prepare(req, client)
        result = await client.send_message_and_collect(
            prep.conv_uuid, prep.prompt, model=prep.model
        )
        return TextPromptResponse(text=result.text, conversation_id=prep.conv_uuid)
