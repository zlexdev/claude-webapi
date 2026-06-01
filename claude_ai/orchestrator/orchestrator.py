"""ClaudeOrchestrator: registers many clients, routes work across them.

Owns a shared `BaseEventBus` and a fixed set of in-process handlers:

  LimitUpdatedEvent            → LimitTracker (selector) + AvailabilityTracker (parking)
  AssistantMessageStartedEvent → MessageMetrics.on_started
  AssistantMessageCompleteEvent→ MessageMetrics.on_complete
  ProxyInvalidEvent            → ProxyBlacklist
  AccountExpiredEvent          → AvailabilityTracker.quarantine + relogin hook
  StreamChunkEvent             → StreamRecorder (opt-in, off by default)

Routing layers on top of the selector:
  - **affinity** — `pick(affinity_key=...)` pins a conversation/user to its account.
  - **availability** — parked (rate-limit cooldown) / quarantined (dead session)
    accounts are excluded; `pick` raises `NoAvailableAccounts` when none are free.
  - **tier** — `pick(min_tier=...)` floors candidates by `AccountTier`.
  - **bulk** — `map()` / `map_prompts()` fan a workload across the pool with
    per-account bulkhead + backpressure + cross-account failover (see `executor.py`).

Persistence: affinity pins + parking state go through a `BaseStorage`
(default in-memory; pass `AioSqliteStorage` / `MongoStorage` / `FileStorage`
for restart-survival). `LimitTracker` / `MessageMetrics` stay ephemeral by design —
they are telemetry rebuilt from the live event stream, not durable state.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable
from typing import Any

from claude_ai.bus.base import BaseEventBus
from claude_ai.bus.memory import MemoryEventBus
from claude_ai.bus.registry import Subscription
from claude_ai.client import ClaudeAIClient
from claude_ai.enums.orchestrator import AccountTier
from claude_ai.events.account import AccountExpiredEvent
from claude_ai.events.message import (
    AssistantMessageCompleteEvent,
    AssistantMessageStartedEvent,
    LimitUpdatedEvent,
    StreamChunkEvent,
)
from claude_ai.events.proxy import ProxyInvalidEvent
from claude_ai.models.streaming import StreamEvent
from claude_ai.orchestrator.affinity import AffinityTracker
from claude_ai.orchestrator.batch import (
    BaseBatchStore,
    BatchRunner,
    StorageBatchStore,
)
from claude_ai.orchestrator.executor import BulkExecutor, BulkResult, TaskFn
from claude_ai.orchestrator.handlers import (
    LimitTracker,
    MessageMetrics,
    ProxyBlacklist,
    StreamRecorder,
)
from claude_ai.orchestrator.scheduling import AvailabilityTracker, NoAvailableAccounts
from claude_ai.orchestrator.selector import (
    BaseClientSelector,
    BusBackedLeastUtilizationSelector,
)
from claude_ai.storage.cache.base import BaseCache
from claude_ai.storage.kv.base import BaseStorage
from claude_ai.storage.kv.memory import MemoryStorage

logger = logging.getLogger("claude_ai.orchestrator")

ReloginHook = Callable[[ClaudeAIClient], Awaitable[bool]]


class ClaudeOrchestrator:
    def __init__(
        self,
        *,
        selector: BaseClientSelector | None = None,
        bus: BaseEventBus | None = None,
        cache: BaseCache | None = None,
        storage: BaseStorage | None = None,
        relogin: ReloginHook | None = None,
        record_stream: bool = False,
        stream_buffer_size: int = 200,
        park_threshold: float = 0.98,
    ) -> None:
        self._clients: dict[str, ClaudeAIClient] = {}
        self._tiers: dict[str, AccountTier] = {}
        self._bus = bus or MemoryEventBus()
        self._cache = cache
        self._owns_storage = storage is None
        self._storage = storage or MemoryStorage()
        self._relogin = relogin
        self._relogin_tasks: set[asyncio.Task[None]] = set()
        self._lock = asyncio.Lock()

        self._limits = LimitTracker()
        self._metrics = MessageMetrics()
        self._proxies = ProxyBlacklist()
        self._affinity = AffinityTracker(self._storage)
        self._availability = AvailabilityTracker(
            self._storage, park_threshold=park_threshold
        )
        self._stream_recorder: StreamRecorder | None = (
            StreamRecorder(max_chunks_per_conv=stream_buffer_size)
            if record_stream
            else None
        )
        self._selector: BaseClientSelector = (
            selector or BusBackedLeastUtilizationSelector(self._limits)
        )

        self._subs: list[Subscription[Any]] = []
        self._started = False

    @property
    def bus(self) -> BaseEventBus:
        return self._bus

    @property
    def cache(self) -> BaseCache | None:
        return self._cache

    @property
    def clients(self) -> dict[str, ClaudeAIClient]:
        return dict(self._clients)

    @property
    def selector(self) -> BaseClientSelector:
        return self._selector

    @property
    def limits(self) -> LimitTracker:
        return self._limits

    @property
    def metrics(self) -> MessageMetrics:
        return self._metrics

    @property
    def proxies(self) -> ProxyBlacklist:
        return self._proxies

    @property
    def affinity(self) -> AffinityTracker:
        return self._affinity

    @property
    def availability(self) -> AvailabilityTracker:
        return self._availability

    @property
    def stream_recorder(self) -> StreamRecorder | None:
        return self._stream_recorder

    async def start(self) -> None:
        if self._started:
            return
        await self._bus.start()
        await self._register_handlers()
        await self._affinity.load()
        await self._availability.load()
        self._started = True

    async def _register_handlers(self) -> None:
        sub = self._bus.subscribe
        self._subs.append(await sub(LimitUpdatedEvent, self._limits.on_event))
        self._subs.append(await sub(LimitUpdatedEvent, self._availability.on_limit))
        self._subs.append(
            await sub(AssistantMessageStartedEvent, self._metrics.on_started)
        )
        self._subs.append(
            await sub(AssistantMessageCompleteEvent, self._metrics.on_complete)
        )
        self._subs.append(await sub(ProxyInvalidEvent, self._proxies.on_invalid))
        self._subs.append(
            await sub(AccountExpiredEvent, self._availability.on_expired)
        )
        self._subs.append(
            await sub(AccountExpiredEvent, self._on_account_expired)
        )
        if self._stream_recorder is not None:
            self._subs.append(
                await sub(StreamChunkEvent, self._stream_recorder.on_chunk)
            )

    async def add(
        self, client: ClaudeAIClient, *, tier: AccountTier = AccountTier.FREE
    ) -> None:
        if not self._started:
            await self.start()
        async with self._lock:
            client.bus = self._bus
            if self._cache is not None and client.cache is None:
                client.cache = self._cache
            self._clients[client.account_id] = client
            self._tiers[client.account_id] = tier
        await client.open()

    async def remove(self, account_id: str) -> ClaudeAIClient | None:
        async with self._lock:
            client = self._clients.pop(account_id, None)
            self._tiers.pop(account_id, None)
        await self._affinity.drop_account(account_id)
        await self._availability.release(account_id)
        if client is not None:
            await client.close()
        return client

    def _tier_ok(self, account_id: str, min_tier: AccountTier | None) -> bool:
        if min_tier is None:
            return True
        return self._tiers.get(account_id, AccountTier.FREE) >= min_tier

    async def pick(
        self,
        *,
        affinity_key: str | None = None,
        min_tier: AccountTier | None = None,
        exclude: Iterable[str] = (),
    ) -> ClaudeAIClient:
        async with self._lock:
            clients = list(self._clients.values())
        if not clients:
            raise RuntimeError("Orchestrator has no clients")
        excluded = set(exclude)

        if affinity_key is not None:
            pinned = self._affinity.get(affinity_key)
            if (
                pinned is not None
                and pinned not in excluded
                and pinned in self._clients
                and self._availability.is_available(pinned)
                and self._tier_ok(pinned, min_tier)
            ):
                return self._clients[pinned]

        candidates = [
            c
            for c in clients
            if c.account_id not in excluded
            and self._availability.is_available(c.account_id)
            and self._tier_ok(c.account_id, min_tier)
        ]
        if not candidates:
            raise NoAvailableAccounts(self._availability.soonest_release())
        chosen = await self._selector.pick(candidates)
        if affinity_key is not None:
            await self._affinity.pin(affinity_key, chosen.account_id)
        return chosen

    async def get(self, account_id: str) -> ClaudeAIClient:
        client = self._clients.get(account_id)
        if client is None:
            raise KeyError(f"No client with account_id={account_id!r}")
        return client

    async def report_expired(self, account_id: str, reason: str = "") -> None:
        """Publish an `AccountExpiredEvent` → quarantine + (optional) relogin."""
        await self._bus.publish(
            AccountExpiredEvent(account_id=account_id, reason=reason)
        )

    async def _on_account_expired(
        self, event: AccountExpiredEvent, _data: dict[str, Any]
    ) -> None:
        if self._relogin is None:
            return
        client = self._clients.get(event.account_id or "")
        if client is None:
            return
        task = asyncio.create_task(self._run_relogin(client))
        self._relogin_tasks.add(task)
        task.add_done_callback(self._relogin_tasks.discard)

    async def _run_relogin(self, client: ClaudeAIClient) -> None:
        try:
            if self._relogin is not None and await self._relogin(client):
                await self._availability.release(client.account_id)
                logger.info("relogin succeeded for %s", client.account_id)
        except Exception:
            logger.exception("relogin failed for %s", client.account_id)

    def executor(self, **kwargs: Any) -> BulkExecutor:
        return BulkExecutor(self, **kwargs)

    def batch_runner(
        self, store: BaseBatchStore | None = None, **kwargs: Any
    ) -> BatchRunner:
        """Resumable batch runner. Defaults to persisting via this pool's storage."""
        return BatchRunner(self, store or StorageBatchStore(self._storage), **kwargs)

    async def map(
        self,
        items: Iterable[Any],
        fn: TaskFn,
        *,
        concurrency_per_account: int = 2,
        max_attempts: int = 3,
        min_tier: AccountTier | None = None,
        affinity_key: Callable[[Any], str | None] | str | None = None,
    ) -> list[BulkResult]:
        executor = BulkExecutor(
            self,
            concurrency_per_account=concurrency_per_account,
            max_attempts=max_attempts,
            min_tier=min_tier,
        )
        return await executor.map(items, fn, affinity_key=affinity_key)

    async def map_prompts(
        self,
        prompts: Iterable[str],
        *,
        concurrency_per_account: int = 2,
        max_attempts: int = 3,
        min_tier: AccountTier | None = None,
    ) -> list[BulkResult]:
        executor = BulkExecutor(
            self,
            concurrency_per_account=concurrency_per_account,
            max_attempts=max_attempts,
            min_tier=min_tier,
        )
        return await executor.map_prompts(prompts)

    async def send_message(
        self,
        prompt: str,
        conv_uuid: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamEvent]:
        client = await self.pick(affinity_key=conv_uuid)
        if conv_uuid is None:
            conv = await client.create_conversation_for_prompt(prompt)
            conv_uuid = conv.uuid
            await self._affinity.pin(conv_uuid, client.account_id)
        return await client.send_message(conv_uuid=conv_uuid, prompt=prompt, **kwargs)

    async def flush(self) -> None:
        await self._bus.flush()

    async def close(self) -> None:
        for task in list(self._relogin_tasks):
            task.cancel()
        self._relogin_tasks.clear()
        async with self._lock:
            clients = list(self._clients.values())
            self._clients.clear()
            self._tiers.clear()
        for client in clients:
            try:
                await client.close()
            except Exception:
                logger.exception("client %s close failed", client.account_id)
        for sub in self._subs:
            try:
                await sub.unsubscribe()
            except Exception:
                pass
        self._subs.clear()
        try:
            await self._bus.flush()
        except Exception:
            pass
        await self._bus.close()
        if self._owns_storage:
            await self._storage.close()
        if self._cache is not None:
            await self._cache.close()
        self._started = False

    async def __aenter__(self) -> ClaudeOrchestrator:
        await self.start()
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        await self.close()
