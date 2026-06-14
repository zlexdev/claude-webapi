"""Auth domain DTOs: Account, ApiKey, KeyInfo, and the admin request bodies."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from claude_ai.enums import AccountTier
from gateway.features.auth.cookies_parse import CookiesInput
from gateway.shared.principal import KeyScope


class Account(BaseModel):
    account_id: str
    org_uuid: str | None = None
    name: str | None = None
    tier: AccountTier = AccountTier.FREE
    cookies: dict[str, str] = Field(default_factory=dict)
    # Per-account UA: cf_clearance is bound to (egress IP, User-Agent), so each jar must
    # be replayed under the exact UA it was harvested with. None → SDK process default.
    user_agent: str | None = None
    revoked: bool = False
    created_at: datetime
    updated_at: datetime


class ApiKey(BaseModel):
    key_id: str
    key_hash: str
    account_id: str
    name: str | None = None
    scope: KeyScope = KeyScope.ACCOUNT
    revoked: bool = False
    created_at: datetime
    last_used_at: datetime | None = None


class KeyInfo(BaseModel):
    """Public view of an ApiKey — never carries the hash."""

    key_id: str
    account_id: str
    name: str | None = None
    scope: KeyScope
    revoked: bool
    created_at: datetime
    last_used_at: datetime | None = None

    @classmethod
    def of(cls, key: ApiKey) -> KeyInfo:
        return cls(
            key_id=key.key_id,
            account_id=key.account_id,
            name=key.name,
            scope=key.scope,
            revoked=key.revoked,
            created_at=key.created_at,
            last_used_at=key.last_used_at,
        )


class AccountInfo(BaseModel):
    """Public view of an Account — never carries cookies."""

    account_id: str
    org_uuid: str | None = None
    name: str | None = None
    tier: AccountTier = AccountTier.FREE
    user_agent: str | None = None
    revoked: bool = False
    created_at: datetime

    @classmethod
    def of(cls, account: Account) -> AccountInfo:
        return cls(
            account_id=account.account_id,
            org_uuid=account.org_uuid,
            name=account.name,
            tier=account.tier,
            user_agent=account.user_agent,
            revoked=account.revoked,
            created_at=account.created_at,
        )


class CreateAccountRequest(BaseModel):
    cookies: CookiesInput
    org_uuid: str | None = None
    name: str | None = None
    tier: str = "free"  # resolved to AccountTier by name in the service
    user_agent: str | None = None  # UA the cookie jar was harvested under


class UpdateAccountCookiesRequest(BaseModel):
    """Refresh a live account's CF session (cookies + optionally the matching UA)."""

    cookies: CookiesInput
    user_agent: str | None = None  # omit to keep the stored UA


class RevokeKeyRequest(BaseModel):
    key_id: str


class GenerateKeyRequest(BaseModel):
    account_id: str | None = None  # bind to an existing account...
    cookies: CookiesInput | None = None  # ...or provision a new one in one shot
    org_uuid: str | None = None
    name: str | None = None
    scope: KeyScope = KeyScope.ACCOUNT
    tier: str = "free"
    user_agent: str | None = None  # UA the cookie jar was harvested under
