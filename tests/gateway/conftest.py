"""Gateway test fixtures: a fake orchestrator + memory-backed container.

No web framework and no network — the whole core (handlers, services, memory stores,
dispatch) is exercised directly through GatewayHandlers.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

import pytest

from claude_ai.models.streaming import ContentBlockDelta, MessageDelta, StopDelta, UsageInfo
from claude_ai.streaming.collector import CompletionResult
from gateway.servers.handlers import GatewayHandlers
from gateway.shared.config import GatewaySettings
from gateway.shared.container import AppContainer


class FakeClient:
    org_uuid = "org-x"

    async def create_conversation_for_prompt(self, prompt: str) -> Any:
        return SimpleNamespace(uuid="conv-new")

    async def send_message_and_collect(self, conv: str, prompt: str, model: str | None = None) -> CompletionResult:
        return CompletionResult(text="Hello there", stop_reason="end_turn", output_tokens=7)

    async def send_message(self, conv: str, prompt: str, model: str | None = None) -> AsyncIterator[Any]:
        # Match the real client: a coroutine that RETURNS the event iterator.
        async def _gen() -> AsyncIterator[Any]:
            yield ContentBlockDelta(
                type="content_block_delta", raw={}, index=0, delta={"type": "text_delta", "text": "Hello"}
            )
            yield ContentBlockDelta(
                type="content_block_delta", raw={}, index=0, delta={"type": "text_delta", "text": " there"}
            )
            yield MessageDelta(
                type="message_delta",
                raw={},
                delta=StopDelta(stop_reason="end_turn", stop_sequence=None),
                usage=UsageInfo(output_tokens=7),
            )

        return _gen()

    async def list_conversations(self, limit: int = 50) -> Any:
        return SimpleNamespace(
            data=[SimpleNamespace(uuid="c1", name="Chat 1", model="claude-sonnet-4-6", updated_at="t", is_starred=False)],
            has_more=False,
            cursor=None,
        )

    async def create_conversation(self, uuid: str, name: str = "", model: str | None = None) -> Any:
        return SimpleNamespace(uuid=uuid, name=name, model=model, updated_at="t", is_starred=False)

    async def get_conversation(self, chat_id: str, tree: bool = True) -> Any:
        msgs = [
            SimpleNamespace(uuid="m0", index=0, sender="human", text="hi", created_at=None),
            SimpleNamespace(uuid="m1", index=1, sender="assistant", text="hello", created_at=None),
        ]
        return SimpleNamespace(chat_messages=msgs)

    async def __call__(self, method: Any, params: Any = None) -> Any:
        return {"ok": True, "method": type(method).__name__}


class FakeOrch:
    def __init__(self) -> None:
        self.added: list[str] = []
        self.removed: list[str] = []

    @property
    def bus(self) -> None:
        return None

    async def start(self) -> None:
        return None

    async def add(self, client: Any, *, tier: Any = None) -> None:
        self.added.append(getattr(client, "account_id", "x"))

    async def remove(self, account_id: str) -> None:
        self.removed.append(account_id)

    async def get(self, account_id: str) -> FakeClient:
        return FakeClient()

    async def close(self) -> None:
        return None


@pytest.fixture
async def container() -> AsyncIterator[AppContainer]:
    settings = GatewaySettings(admin_token="admintok", db="memory")
    container = AppContainer(settings, orchestrator=FakeOrch())
    await container.open()
    yield container
    await container.close()


@pytest.fixture
def handlers(container: AppContainer) -> GatewayHandlers:
    return GatewayHandlers(container)
