"""ChatService: list / create chats and page a chat's messages.

Conversation listing rides the SDK's own pagination; message pagination is gateway-side
over the full ``chat_messages`` list claude returns, using the monotonic message
``index`` as an opaque cursor (R-9). "Send to a chat" is composed at the handler layer
(completion service + ``conversation_id``) to avoid feature-to-feature coupling.
"""

from __future__ import annotations

import uuid

from claude_ai.orchestrator import ClaudeOrchestrator
from gateway.base.service import BaseService
from gateway.features.chats.schemas.dtos import ChatSummary, MessageDTO
from gateway.shared.accounts import resolve_client
from gateway.shared.principal import Principal
from gateway.shared.schemas.pagination import Page

_SENDER_ROLE = {"human": "user", "assistant": "assistant"}


class ChatService(BaseService):
    def __init__(self, orchestrator: ClaudeOrchestrator) -> None:
        self._orch = orchestrator

    async def list_chats(self, principal: Principal, *, limit: int) -> Page[ChatSummary]:
        client = await resolve_client(self._orch, principal.account_id)
        paged = await client.list_conversations(limit=limit)
        data = [
            ChatSummary(
                id=c.uuid,
                name=c.name,
                model=c.model,
                updated_at=c.updated_at,
                is_starred=c.is_starred,
            )
            for c in paged.data
        ]
        return Page(data=data, has_more=paged.has_more, cursor=paged.cursor)

    async def create_chat(
        self, principal: Principal, *, name: str | None, model: str | None
    ) -> ChatSummary:
        client = await resolve_client(self._orch, principal.account_id)
        conv = await client.create_conversation(
            uuid=str(uuid.uuid4()), name=name or "", model=model
        )
        return ChatSummary(
            id=conv.uuid,
            name=conv.name,
            model=conv.model,
            updated_at=conv.updated_at,
            is_starred=conv.is_starred,
        )

    async def messages(
        self, principal: Principal, chat_id: str, *, limit: int, cursor: str | None
    ) -> Page[MessageDTO]:
        client = await resolve_client(self._orch, principal.account_id)
        conv = await client.get_conversation(chat_id, tree=False)
        start = int(cursor) if cursor and cursor.isdigit() else 0
        ordered = sorted(conv.chat_messages, key=lambda m: m.index)
        window = [m for m in ordered if m.index >= start]
        page_items = window[:limit]
        has_more = len(window) > limit
        next_cursor = (
            str(page_items[-1].index + 1) if has_more and page_items else None
        )
        data = [
            MessageDTO(
                id=m.uuid,
                role=_SENDER_ROLE.get(m.sender, m.sender),
                text=m.text,
                index=m.index,
                created_at=m.created_at,
            )
            for m in page_items
        ]
        return Page(data=data, has_more=has_more, cursor=next_cursor)
