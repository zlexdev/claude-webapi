"""Memory auth-store tests — keyset cursor pagination parity + lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from gateway.features.auth.schemas.dtos import Account, ApiKey
from gateway.shared.principal import KeyScope
from gateway.features.auth.store.memory import MemoryAccountStore, MemoryApiKeyStore

BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _account(i: int) -> Account:
    when = BASE + timedelta(minutes=i)
    return Account(account_id=f"acc{i}", cookies={"k": str(i)}, created_at=when, updated_at=when)


async def test_account_keyset_pagination() -> None:
    store = MemoryAccountStore()
    for i in range(5):
        await store.upsert(_account(i))
    p1 = await store.page(limit=2)
    assert [a.account_id for a in p1.data] == ["acc4", "acc3"] and p1.has_more
    p2 = await store.page(limit=2, cursor=p1.cursor)
    assert [a.account_id for a in p2.data] == ["acc2", "acc1"]
    p3 = await store.page(limit=2, cursor=p2.cursor)
    assert [a.account_id for a in p3.data] == ["acc0"] and not p3.has_more


async def test_account_iterate_all_and_revoke() -> None:
    store = MemoryAccountStore()
    for i in range(3):
        await store.upsert(_account(i))
    await store.revoke("acc1")
    visible = [a.account_id async for a in store.iterate_all()]
    assert "acc1" not in visible and len(visible) == 2
    everything = [a.account_id async for a in store.iterate_all(include_revoked=True)]
    assert "acc1" in everything


async def test_apikey_store() -> None:
    store = MemoryApiKeyStore()
    key = ApiKey(
        key_id="k1", key_hash="h1", account_id="acc0", scope=KeyScope.ACCOUNT, created_at=BASE
    )
    await store.create(key)
    assert (await store.get_by_hash("h1")).key_id == "k1"  # type: ignore[union-attr]
    await store.touch("k1", BASE + timedelta(hours=1))
    assert (await store.get("k1")).last_used_at == BASE + timedelta(hours=1)  # type: ignore[union-attr]
    await store.revoke("k1")
    assert (await store.get("k1")).revoked  # type: ignore[union-attr]
    page = await store.page(account_id="acc0", limit=10)
    assert len(page.data) == 1
