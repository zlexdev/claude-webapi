"""Persistent, resumable batch execution over the account pool (#9).

`BatchRunner.run(job_id, items, fn)` fans `items` across the pool via
`BulkExecutor`, persisting each item's outcome through a `BaseBatchStore` as it
completes. Re-running the same `job_id` after a crash skips already-DONE items
and retries the rest — so a 10k-item job survives a restart.

`BaseBatchStore` is the **extension point**: the default `StorageBatchStore`
rides the generic `storage/kv` backends (memory / file / sqlite / mongo), but a
project can subclass it to persist into its own Postgres / queue / table.

Payloads MUST be JSON-serializable (they are written to the store).
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

from claude_ai.enums.orchestrator import (
    AccountTier,
    BatchItemStatus,
    BatchStatus,
)
from claude_ai.orchestrator.executor import BulkExecutor
from claude_ai.storage.kv.base import BaseStorage

if TYPE_CHECKING:
    from claude_ai.client import ClaudeAIClient
    from claude_ai.orchestrator.orchestrator import ClaudeOrchestrator

_JOBS_NS = "batch_jobs"


def _items_ns(job_id: str) -> str:
    return f"batch:{job_id}"


@dataclass(slots=True)
class BatchItem:
    index: int
    payload: Any
    status: BatchItemStatus = BatchItemStatus.PENDING
    result: Any = None
    error: str | None = None
    attempts: int = 0
    account_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = str(self.status)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BatchItem:
        return cls(
            index=int(data["index"]),
            payload=data.get("payload"),
            status=BatchItemStatus(data.get("status", BatchItemStatus.PENDING)),
            result=data.get("result"),
            error=data.get("error"),
            attempts=int(data.get("attempts", 0)),
            account_id=data.get("account_id"),
        )


@dataclass(slots=True)
class BatchJob:
    id: str
    total: int
    status: BatchStatus = BatchStatus.RUNNING
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = str(self.status)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BatchJob:
        return cls(
            id=str(data["id"]),
            total=int(data["total"]),
            status=BatchStatus(data.get("status", BatchStatus.RUNNING)),
            created_at=float(data.get("created_at", 0.0)),
        )


class BaseBatchStore(ABC):
    """Extension point — subclass to persist batches into a project's own store."""

    @abstractmethod
    async def create(self, job: BatchJob) -> None: ...

    @abstractmethod
    async def get(self, job_id: str) -> BatchJob | None: ...

    @abstractmethod
    async def set_status(self, job_id: str, status: BatchStatus) -> None: ...

    @abstractmethod
    async def save_item(self, job_id: str, item: BatchItem) -> None: ...

    @abstractmethod
    async def items(self, job_id: str) -> list[BatchItem]: ...

    @abstractmethod
    async def list_jobs(self) -> list[str]: ...

    async def pending(self, job_id: str) -> list[BatchItem]:
        return [
            it
            for it in await self.items(job_id)
            if it.status is not BatchItemStatus.DONE
        ]


class StorageBatchStore(BaseBatchStore):
    """Default `BaseBatchStore` backed by a generic `storage/kv` `BaseStorage`."""

    def __init__(self, storage: BaseStorage) -> None:
        self._s = storage

    async def create(self, job: BatchJob) -> None:
        await self._s.set(_JOBS_NS, job.id, job.to_dict())

    async def get(self, job_id: str) -> BatchJob | None:
        data = await self._s.get(_JOBS_NS, job_id)
        return BatchJob.from_dict(data) if data else None

    async def set_status(self, job_id: str, status: BatchStatus) -> None:
        job = await self.get(job_id)
        if job is not None:
            job.status = status
            await self.create(job)

    async def save_item(self, job_id: str, item: BatchItem) -> None:
        await self._s.set(_items_ns(job_id), str(item.index), item.to_dict())

    async def items(self, job_id: str) -> list[BatchItem]:
        raw = await self._s.items(_items_ns(job_id))
        return sorted(
            (BatchItem.from_dict(v) for v in raw.values()), key=lambda it: it.index
        )

    async def list_jobs(self) -> list[str]:
        return list((await self._s.items(_JOBS_NS)).keys())


class BatchRunner:
    def __init__(
        self,
        orchestrator: ClaudeOrchestrator,
        store: BaseBatchStore,
        *,
        concurrency_per_account: int = 2,
        max_attempts: int = 3,
        min_tier: AccountTier | None = None,
    ) -> None:
        self._orch = orchestrator
        self._store = store
        self._per_account = concurrency_per_account
        self._max_attempts = max_attempts
        self._min_tier = min_tier

    async def run(
        self,
        job_id: str,
        items: Iterable[Any],
        fn: Callable[[ClaudeAIClient, Any], Awaitable[Any]],
        *,
        affinity_key: Callable[[Any], str | None] | None = None,
    ) -> BatchJob:
        existing = await self._store.get(job_id)
        if existing is None:
            payloads = list(items)
            await self._store.create(BatchJob(id=job_id, total=len(payloads)))
            records = [BatchItem(index=i, payload=p) for i, p in enumerate(payloads)]
            for record in records:
                await self._store.save_item(job_id, record)
        else:
            await self._store.set_status(job_id, BatchStatus.RUNNING)
            records = await self._store.pending(job_id)

        if records:
            await self._execute(job_id, records, fn, affinity_key)

        all_items = await self._store.items(job_id)
        complete = all(it.status is BatchItemStatus.DONE for it in all_items)
        await self._store.set_status(
            job_id, BatchStatus.COMPLETED if complete else BatchStatus.PARTIAL
        )
        job = await self._store.get(job_id)
        assert job is not None  # created above
        return job

    async def _execute(
        self,
        job_id: str,
        records: list[BatchItem],
        fn: Callable[[ClaudeAIClient, Any], Awaitable[Any]],
        affinity_key: Callable[[Any], str | None] | None,
    ) -> None:
        executor = BulkExecutor(
            self._orch,
            concurrency_per_account=self._per_account,
            max_attempts=self._max_attempts,
            min_tier=self._min_tier,
        )

        async def task(client: ClaudeAIClient, record: BatchItem) -> Any:
            return await fn(client, record.payload)

        async def on_result(br: Any) -> None:
            record = records[br.index]
            record.status = BatchItemStatus.DONE if br.ok else BatchItemStatus.FAILED
            record.result = br.value
            record.error = br.error
            record.attempts = br.attempts
            record.account_id = br.account_id
            await self._store.save_item(job_id, record)

        wrapped_key = (
            (lambda record: affinity_key(record.payload))
            if affinity_key is not None
            else None
        )
        await executor.map(records, task, affinity_key=wrapped_key, on_result=on_result)

    async def results(self, job_id: str) -> list[BatchItem]:
        return await self._store.items(job_id)

    async def status(self, job_id: str) -> BatchJob | None:
        return await self._store.get(job_id)
