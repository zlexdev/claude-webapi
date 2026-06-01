"""Integration tests against the real claude.ai API.

Skipped automatically unless cookies are provided via:
  - file: tests/.cookies.local (one-line cookie string)
  - env:  CLAUDE_COOKIES (full cookie string)
  - env:  CLAUDE_SESSION_KEY (sessionKey only — limited; /completion may CF-403)

Run only the integration set:  pytest tests/test_integration_live.py -v
"""

from __future__ import annotations

import os
import uuid as _uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from claude_ai import ClaudeAIClient
from tests.live_runner import build_client, parse_cookie_string

_COOKIES_FILE = Path(__file__).parent / ".cookies.local"


def _load_cookies() -> dict[str, str] | None:
    if _COOKIES_FILE.exists():
        raw = _COOKIES_FILE.read_text(encoding="utf-8").strip()
        if raw:
            return parse_cookie_string(raw)
    env_full = os.environ.get("CLAUDE_COOKIES", "").strip()
    if env_full:
        return parse_cookie_string(env_full)
    sk = os.environ.get("CLAUDE_SESSION_KEY", "").strip()
    if sk:
        return {"sessionKey": sk}
    return None


_COOKIES = _load_cookies()
pytestmark = pytest.mark.skipif(
    _COOKIES is None or "sessionKey" not in _COOKIES,
    reason="No claude.ai cookies provided (drop one in tests/.cookies.local).",
)


@pytest.fixture
async def client() -> AsyncIterator[ClaudeAIClient]:
    assert _COOKIES is not None
    c = build_client(_COOKIES)
    c.org_uuid = _COOKIES.get("lastActiveOrg", "")
    async with c:
        if not c.org_uuid:
            from tests._inline_methods import ListOrganizations

            orgs = await c(ListOrganizations())
            assert orgs, "could not discover org_uuid"
            c.org_uuid = orgs[0]["uuid"]
        yield c


async def test_get_profile(client: ClaudeAIClient) -> None:
    profile = await client.get_profile()
    assert profile is not None


async def test_get_organization(client: ClaudeAIClient) -> None:
    org = await client.get_organization()
    assert org.uuid == client.org_uuid
    assert org.name


async def test_get_subscription(client: ClaudeAIClient) -> None:
    sub = await client.get_subscription()
    assert sub.status is not None


async def test_get_credits(client: ClaudeAIClient) -> None:
    credits = await client.get_credits()
    assert credits.remaining >= 0


async def test_get_styles(client: ClaudeAIClient) -> None:
    styles = await client.get_styles()
    assert isinstance(styles, list)
    assert len(styles) >= 1
    assert all(s.name for s in styles)


async def test_list_conversations(client: ClaudeAIClient) -> None:
    page = await client.list_conversations(limit=3)
    assert hasattr(page, "data")


async def test_full_chat_lifecycle(client: ClaudeAIClient) -> None:
    """Create → send → followup → title → rename → delete."""
    conv_uuid = str(_uuid.uuid4())
    conv = await client.create_conversation(uuid=conv_uuid)
    try:
        assert conv.uuid == conv_uuid

        first = await client.send_message_and_collect(
            conv_uuid, "Reply with exactly the word: pong"
        )
        assert first.text.strip().lower() == "pong"
        assert first.message_uuid

        second = await client.send_message_and_collect(
            conv_uuid, "Now reply with exactly the word: pang"
        )
        assert second.text.strip().lower() == "pang"
        assert second.message_uuid and second.message_uuid != first.message_uuid

        title = await client.generate_title(
            conv_uuid, message_content="ping pong exchange"
        )
        assert isinstance(title, str)

        await client.update_conversation(conv_uuid, name="claude_lib integration test")
    finally:
        await client.delete_conversation(conv_uuid)


async def test_send_message_streams_events(client: ClaudeAIClient) -> None:
    """Verify we receive multiple typed StreamEvent objects, not just an empty iter."""
    conv_uuid = str(_uuid.uuid4())
    await client.create_conversation(uuid=conv_uuid)
    try:
        events = await client.send_message(
            conv_uuid, "Reply with exactly: pong"
        )
        from claude_ai.models.streaming import (
            ContentBlockDelta,
            MessageStart,
            MessageStop,
        )

        seen_start = seen_stop = False
        deltas = 0
        async for evt in events:
            if isinstance(evt, MessageStart):
                seen_start = True
            elif isinstance(evt, ContentBlockDelta):
                deltas += 1
            elif isinstance(evt, MessageStop):
                seen_stop = True

        assert seen_start and seen_stop
        assert deltas >= 1
    finally:
        await client.delete_conversation(conv_uuid)


async def test_orchestrator_handlers_observe_real_stream() -> None:
    """End-to-end: orchestrator wraps a live client, dispatches a message, and
    its bus-registered handlers see message-started, message-complete, and
    limit-updated events from the real SSE stream."""
    from claude_ai import (
        BusBackedLeastUtilizationSelector,
        ClaudeOrchestrator,
        MemoryEventBus,
    )
    from tests.live_runner import build_client

    assert _COOKIES is not None

    bus = MemoryEventBus(mode="inline")
    orch = ClaudeOrchestrator(bus=bus)
    await orch.start()

    live_client = build_client(_COOKIES)
    live_client.org_uuid = _COOKIES.get("lastActiveOrg", "")
    try:
        await orch.add(live_client)
        assert isinstance(orch.selector, BusBackedLeastUtilizationSelector)

        conv_uuid = str(_uuid.uuid4())
        conv = await live_client.create_conversation(uuid=conv_uuid)
        try:
            result = await live_client.send_message_and_collect(
                conv.uuid, "Reply with exactly: pong"
            )
            await orch.flush()
            assert result.text.strip().lower() == "pong"

            account = live_client.account_id
            metrics = orch.metrics.get(account)
            assert metrics.started >= 1
            assert metrics.completed >= 1
            limit = orch.limits.get(account)
            assert limit.score() > 0.0 or limit.representative_claim is not None
        finally:
            await live_client.delete_conversation(conv.uuid)
    finally:
        await orch.close()
