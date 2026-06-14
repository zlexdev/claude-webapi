"""Memory auth-store tests — keyset cursor pagination parity + lifecycle + cookie cipher."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from gateway.features.auth.schemas.dtos import Account, ApiKey
from gateway.shared.principal import KeyScope
from gateway.features.auth.store.memory import MemoryAccountStore, MemoryApiKeyStore

BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _account(i: int) -> Account:
    when = BASE + timedelta(minutes=i)
    return Account(account_id=f"acc{i}", cookies={"k": str(i)}, created_at=when, updated_at=when)


def test_cookie_cipher_round_trip() -> None:
    pytest.importorskip("cryptography")
    from cryptography.fernet import Fernet

    from gateway.features.auth.cipher import CookieCipher

    cipher = CookieCipher(Fernet.generate_key().decode())
    jar = {"sessionKey": "sk-ant-sid01-x", "cf_clearance": "cf"}
    token = cipher.encrypt(jar)
    assert isinstance(token, str) and "sessionKey" not in token  # opaque ciphertext
    assert cipher.decrypt(token) == jar


def test_cookie_cipher_wrong_key_raises() -> None:
    pytest.importorskip("cryptography")
    from cryptography.fernet import Fernet

    from gateway.features.auth.cipher import CookieCipher
    from gateway.features.auth.errors import CookieDecryptError

    token = CookieCipher(Fernet.generate_key().decode()).encrypt({"a": "b"})
    with pytest.raises(CookieDecryptError):
        CookieCipher(Fernet.generate_key().decode()).decrypt(token)


def test_per_account_user_agent_flows_into_session_headers() -> None:
    from claude_ai.methods.account.get_profile import GetProfile
    from claude_ai.session import HttpSession

    account = Account(
        account_id="acc_ua",
        cookies={"sessionKey": "s"},
        user_agent="Custom-UA/9",
        created_at=BASE,
        updated_at=BASE,
    )
    session = HttpSession(account.account_id, cookies=account.cookies, user_agent=account.user_agent)
    req = session._build_transport_request(GetProfile(), None)
    assert req.headers["user-agent"] == "Custom-UA/9"

    # No per-account UA → process-global default applies.
    default_session = HttpSession(account.account_id, cookies=account.cookies)
    default_req = default_session._build_transport_request(GetProfile(), None)
    assert default_req.headers["user-agent"] == default_session.settings.user_agent


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
