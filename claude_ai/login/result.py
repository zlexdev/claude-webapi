"""LoginResult: the outcome of a completed magic-link login."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class LoginResult:
    email: str
    cookies: dict[str, str]
    org_uuid: str | None = None
    account: dict[str, Any] | None = None
    secret: str | None = None
