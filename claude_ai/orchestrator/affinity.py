"""AffinityTracker: sticky routing of an affinity key to one account.

claude.ai conversations are account-scoped — a conversation created on account A
cannot be continued on account B. Any multi-turn flow MUST pin its key
(conversation uuid, or an end-user id) to the account that created it.

State is mirrored in memory (sync `get`) and persisted through a `BaseStorage`
so pins survive a restart — losing them silently breaks every in-flight chat.
"""

from __future__ import annotations

from claude_ai.storage.kv.base import BaseStorage, StorageNamespace


class AffinityTracker:
    def __init__(self, store: BaseStorage | None = None) -> None:
        self._pin: dict[str, str] = {}
        self._store = store

    async def load(self) -> None:
        if self._store is not None:
            raw = await self._store.items(StorageNamespace.AFFINITY)
            self._pin = {k: str(v) for k, v in raw.items()}

    def get(self, key: str) -> str | None:
        return self._pin.get(key)

    async def pin(self, key: str, account_id: str) -> None:
        if self._pin.get(key) == account_id:
            return
        self._pin[key] = account_id
        if self._store is not None:
            await self._store.set(StorageNamespace.AFFINITY, key, account_id)

    async def unpin(self, key: str) -> None:
        self._pin.pop(key, None)
        if self._store is not None:
            await self._store.delete(StorageNamespace.AFFINITY, key)

    async def drop_account(self, account_id: str) -> None:
        """Remove every pin to an account that left the pool."""
        for key in [k for k, v in self._pin.items() if v == account_id]:
            del self._pin[key]
            if self._store is not None:
                await self._store.delete(StorageNamespace.AFFINITY, key)

    def all(self) -> dict[str, str]:
        return dict(self._pin)
