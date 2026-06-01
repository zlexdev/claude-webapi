"""BulkExecutor: fan a list of tasks across the account pool.

Throughput primitives, all on top of the existing selector + trackers:
  - **per-account semaphore** (bulkhead): at most `concurrency_per_account` in-flight
    tasks hit one account, even if the selector would pile them on.
  - **bounded queue** (backpressure): producer blocks once the queue is full.
  - **cross-account failover + DLQ**: a task that 429s / 401s / 403s is retried on a
    different account up to `max_attempts`; exhausted tasks land in `dead_letters`.
  - **affinity**: pass `affinity_key=callable(item)->str` to pin multi-turn items.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from claude_ai.exceptions import (
    APIError,
    AuthError,
    ForbiddenError,
    NetworkError,
    RateLimitError,
    StreamError,
)
from claude_ai.orchestrator.scheduling import NoAvailableAccounts

if TYPE_CHECKING:
    from claude_ai.client import ClaudeAIClient
    from claude_ai.enums.orchestrator import AccountTier
    from claude_ai.orchestrator.orchestrator import ClaudeOrchestrator

TaskFn = Callable[["ClaudeAIClient", Any], Awaitable[Any]]
AffinityKey = Callable[[Any], "str | None"] | str | None
OnResult = Callable[["BulkResult"], Awaitable[None]]


@dataclass(slots=True)
class BulkResult:
    index: int
    item: Any
    ok: bool
    value: Any = None
    error: str | None = None
    account_id: str | None = None
    attempts: int = 0


@dataclass(slots=True)
class _Task:
    index: int
    item: Any
    affinity_key: str | None


class BulkExecutor:
    def __init__(
        self,
        orchestrator: ClaudeOrchestrator,
        *,
        concurrency_per_account: int = 2,
        max_attempts: int = 3,
        min_tier: AccountTier | None = None,
        max_park_waits: int = 20,
        park_wait_cap: float = 30.0,
    ) -> None:
        self._orch = orchestrator
        self._per_account = concurrency_per_account
        self._max_attempts = max_attempts
        self._min_tier = min_tier
        self._max_park_waits = max_park_waits
        self._park_wait_cap = park_wait_cap
        self._sems: dict[str, asyncio.Semaphore] = {}
        self.dead_letters: list[BulkResult] = []

    def _sem(self, account_id: str) -> asyncio.Semaphore:
        sem = self._sems.get(account_id)
        if sem is None:
            sem = asyncio.Semaphore(self._per_account)
            self._sems[account_id] = sem
        return sem

    @staticmethod
    def _key(affinity_key: AffinityKey, item: Any) -> str | None:
        if callable(affinity_key):
            return affinity_key(item)
        return affinity_key

    async def map(
        self,
        items: Iterable[Any],
        fn: TaskFn,
        *,
        affinity_key: AffinityKey = None,
        on_result: OnResult | None = None,
    ) -> list[BulkResult]:
        tasks = [
            _Task(i, item, self._key(affinity_key, item))
            for i, item in enumerate(items)
        ]
        results: list[BulkResult | None] = [None] * len(tasks)
        if not tasks:
            return []
        n_slots = max(1, len(self._orch.clients) * self._per_account)
        queue: asyncio.Queue[_Task] = asyncio.Queue(maxsize=n_slots * 2)
        workers = [
            asyncio.create_task(self._worker(queue, fn, results, on_result))
            for _ in range(n_slots)
        ]
        try:
            for task in tasks:
                await queue.put(task)  # blocks when full → backpressure
            await queue.join()
        finally:
            for w in workers:
                w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
        return [r for r in results if r is not None]

    async def map_prompts(
        self, prompts: Iterable[str], **kwargs: Any
    ) -> list[BulkResult]:
        async def _send(client: ClaudeAIClient, prompt: str) -> Any:
            conv = await client.create_conversation_for_prompt(prompt)
            return await client.send_message_and_collect(conv.uuid, prompt)

        return await self.map(prompts, _send, **kwargs)

    async def _worker(
        self,
        queue: asyncio.Queue[_Task],
        fn: TaskFn,
        results: list[BulkResult | None],
        on_result: OnResult | None,
    ) -> None:
        while True:
            task = await queue.get()
            try:
                result = await self._run_one(task, fn)
                results[task.index] = result
                if not result.ok:
                    self.dead_letters.append(result)
                if on_result is not None:
                    await on_result(result)
            finally:
                queue.task_done()

    async def _run_one(self, task: _Task, fn: TaskFn) -> BulkResult:
        tried: set[str] = set()
        attempts = 0
        waits = 0
        last_err = "no attempt made"
        while attempts < self._max_attempts:
            try:
                client = await self._orch.pick(
                    affinity_key=task.affinity_key,
                    min_tier=self._min_tier,
                    exclude=tried,
                )
            except NoAvailableAccounts as exc:
                waits += 1
                if waits > self._max_park_waits:
                    last_err = "all accounts parked/quarantined"
                    break
                await asyncio.sleep(self._wait_delay(exc.soonest_release))
                continue
            except RuntimeError as exc:  # no clients / all excluded
                last_err = str(exc)
                break

            attempts += 1
            account_id = client.account_id
            async with self._sem(account_id):
                try:
                    value = await fn(client, task.item)
                    return BulkResult(
                        task.index, task.item, ok=True, value=value,
                        account_id=account_id, attempts=attempts,
                    )
                except RateLimitError as exc:
                    until = time.time() + exc.retry_after if exc.retry_after else None
                    await self._orch.availability.park(account_id, until, "429")
                    tried.add(account_id)
                    last_err = str(exc)
                except AuthError as exc:
                    await self._orch.report_expired(account_id, "401 during task")
                    tried.add(account_id)
                    last_err = str(exc)
                except ForbiddenError as exc:
                    tried.add(account_id)
                    last_err = str(exc)
                except (APIError, NetworkError, StreamError) as exc:
                    last_err = str(exc)  # transient: retry, account stays eligible
                except Exception as exc:  # noqa: BLE001 — unknown task error, don't hammer the pool
                    last_err = str(exc)
                    break
        return BulkResult(
            task.index, task.item, ok=False, error=last_err, attempts=attempts
        )

    def _wait_delay(self, soonest_release: float | None) -> float:
        if soonest_release is None:
            return min(self._park_wait_cap, 5.0)
        return max(0.5, min(self._park_wait_cap, soonest_release - time.time()))
