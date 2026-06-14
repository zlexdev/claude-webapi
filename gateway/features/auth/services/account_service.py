"""AccountService: provision a claude.ai account from cookies and wire it into the pool.

Provisioning persists the account (DB is the source of truth) then registers a live
client with the orchestrator. ``orch.add`` opens the client and binds it to the shared
bus, so we never call ``client.open()`` ourselves. Startup rehydration rebuilds every
non-revoked account's client via a cursor scan (never a full unbounded load).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from claude_ai import ClaudeAIClient
from claude_ai.enums import AccountTier
from claude_ai.orchestrator import ClaudeOrchestrator
from claude_ai.session import HttpSession
from gateway.base.service import BaseService
from gateway.features.auth.cookies_parse import CookiesInput, parse_cookies
from gateway.features.auth.errors import AccountNotFound
from gateway.features.auth.schemas.dtos import Account, AccountInfo
from gateway.features.auth.store.base import BaseAccountStore
from gateway.shared.logging import get_logger
from gateway.shared.schemas.pagination import Page

log = get_logger("auth.account")


def resolve_tier(name: str) -> AccountTier:
    try:
        return AccountTier[name.strip().upper()]
    except KeyError:
        return AccountTier.FREE


class AccountService(BaseService):
    def __init__(self, accounts: BaseAccountStore, orchestrator: ClaudeOrchestrator) -> None:
        self._accounts = accounts
        self._orch = orchestrator

    def _build_client(self, account: Account) -> ClaudeAIClient:
        session = HttpSession(
            account.account_id,
            cookies=account.cookies,
            user_agent=account.user_agent,
            bus=self._orch.bus,
        )
        return ClaudeAIClient(
            account.account_id,
            session=session,
            org_uuid=account.org_uuid or "",
            bus=self._orch.bus,
        )

    async def provision(
        self,
        cookies: CookiesInput,
        *,
        org_uuid: str | None,
        name: str | None,
        tier: AccountTier,
        user_agent: str | None = None,
    ) -> Account:
        parsed = parse_cookies(cookies)
        now = datetime.now(UTC)
        account = Account(
            account_id=f"acc_{uuid.uuid4().hex}",
            org_uuid=org_uuid,
            name=name,
            tier=tier,
            cookies=parsed,
            user_agent=user_agent,
            created_at=now,
            updated_at=now,
        )
        await self._accounts.upsert(account)
        await self._orch.add(self._build_client(account), tier=tier)
        log.info("account provisioned", extra={"account_id": account.account_id})
        return account

    async def update_cookies(
        self,
        account_id: str,
        cookies: CookiesInput,
        *,
        user_agent: str | None = None,
    ) -> Account:
        """Refresh a (live) account's CF session and rebuild its pooled client.

        cf_clearance / __cf_bm expire in hours; this is the re-provision-free path.
        ``user_agent=None`` keeps the stored UA. A revoked account is updated at rest
        but not re-added to the pool (it was never in it).
        """
        account = await self.get(account_id)  # raises AccountNotFound
        updated = account.model_copy(
            update={
                "cookies": parse_cookies(cookies),
                "user_agent": user_agent if user_agent is not None else account.user_agent,
                "updated_at": datetime.now(UTC),
            }
        )
        await self._accounts.upsert(updated)
        if not updated.revoked:
            await self._orch.remove(account_id)  # closes the stale-cookie client
            await self._orch.add(self._build_client(updated), tier=updated.tier)
        log.info("account cookies refreshed", extra={"account_id": account_id})
        return updated

    async def rehydrate_all(self) -> int:
        count = 0
        async for account in self._accounts.iterate_all():
            await self._orch.add(self._build_client(account), tier=account.tier)
            count += 1
        log.info("accounts rehydrated", extra={"count": count})
        return count

    async def get(self, account_id: str) -> Account:
        account = await self._accounts.get(account_id)
        if account is None:
            raise AccountNotFound(f"account {account_id!r} not found")
        return account

    async def page(self, *, limit: int, cursor: str | None) -> Page[AccountInfo]:
        page = await self._accounts.page(include_revoked=True, limit=limit, cursor=cursor)
        return Page(
            data=[AccountInfo.of(a) for a in page.data],
            has_more=page.has_more,
            cursor=page.cursor,
        )

    def availability(self, account_id: str) -> dict[str, Any]:
        return {
            "available": self._orch.availability.is_available(account_id),
            "in_flight": self._orch.metrics.in_flight(account_id),
            "utilization": self._orch.limits.get(account_id).score(),
        }
