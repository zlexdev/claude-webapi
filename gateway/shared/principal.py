"""Principal + KeyScope — the authenticated caller, shared across all features.

Lives in ``shared`` (not ``features/auth``) because completion / chats / methods all
receive a Principal; keeping it here avoids feature-to-feature imports (backend law #3).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class KeyScope(StrEnum):
    ACCOUNT = "account"  # may only target its own bound account
    ADMIN = "admin"  # may target any registered account (D7)


class Principal(BaseModel):
    key_id: str
    account_id: str
    scope: KeyScope
    org_uuid: str | None = None

    @property
    def is_admin(self) -> bool:
        return self.scope is KeyScope.ADMIN
