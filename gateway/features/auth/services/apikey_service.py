"""ApiKeyService: mint / authenticate / list / revoke API keys.

A key may be generated against an existing ``account_id`` or straight from ``cookies``
(provision + key in one shot). Authentication hashes the inbound bearer and looks it up
in constant-time-safe storage; ``touch`` (last_used_at) is best-effort and must be called
fire-and-forget by the caller so a DB hiccup never fails auth.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from gateway.base.service import BaseService
from gateway.features.auth.errors import (
    InvalidApiKey,
    KeyTargetRequired,
    MissingApiKey,
    RevokedApiKey,
)
from gateway.features.auth.keys import generate_key, hash_key
from gateway.features.auth.schemas.dtos import ApiKey, GenerateKeyRequest, KeyInfo
from gateway.shared.principal import Principal
from gateway.features.auth.services.account_service import AccountService, resolve_tier
from gateway.features.auth.store.base import BaseApiKeyStore
from gateway.shared.schemas.pagination import Page


def _strip_bearer(header: str) -> str:
    value = header.strip()
    if value.lower().startswith("bearer "):
        return value[7:].strip()
    return value


class ApiKeyService(BaseService):
    def __init__(self, keys: BaseApiKeyStore, account_service: AccountService) -> None:
        self._keys = keys
        self._accounts = account_service

    async def generate(self, req: GenerateKeyRequest) -> tuple[KeyInfo, str]:
        if req.cookies is not None:
            account = await self._accounts.provision(
                req.cookies,
                org_uuid=req.org_uuid,
                name=req.name,
                tier=resolve_tier(req.tier),
                user_agent=req.user_agent,
            )
            account_id = account.account_id
        elif req.account_id:
            await self._accounts.get(req.account_id)  # raises AccountNotFound if absent
            account_id = req.account_id
        else:
            raise KeyTargetRequired()

        raw, key_hash = generate_key()
        key = ApiKey(
            key_id=f"key_{uuid.uuid4().hex}",
            key_hash=key_hash,
            account_id=account_id,
            name=req.name,
            scope=req.scope,
            created_at=datetime.now(UTC),
        )
        await self._keys.create(key)
        return KeyInfo.of(key), raw

    async def authenticate(self, authorization: str | None) -> Principal:
        if not authorization:
            raise MissingApiKey()
        token = _strip_bearer(authorization)
        if not token:
            raise MissingApiKey()
        key = await self._keys.get_by_hash(hash_key(token))
        if key is None:
            raise InvalidApiKey()
        if key.revoked:
            raise RevokedApiKey()
        return Principal(key_id=key.key_id, account_id=key.account_id, scope=key.scope)

    async def page(
        self, *, account_id: str | None, limit: int, cursor: str | None
    ) -> Page[KeyInfo]:
        page = await self._keys.page(account_id=account_id, limit=limit, cursor=cursor)
        return Page(
            data=[KeyInfo.of(k) for k in page.data],
            has_more=page.has_more,
            cursor=page.cursor,
        )

    async def revoke(self, key_id: str) -> None:
        await self._keys.revoke(key_id)

    async def touch(self, key_id: str) -> None:
        await self._keys.touch(key_id, datetime.now(UTC))
