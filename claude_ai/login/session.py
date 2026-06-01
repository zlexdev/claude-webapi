"""MagicLinkLogin: the stateful email magic-link login flow.

`request(email)` sends the login email; `complete(link)` parses the link, verifies it
(claude.ai sets the session cookies, absorbed by `HttpSession`), bootstraps the account
(org uuid from the verify response), and returns the cookies in a `LoginResult`.

The same instance should span `request` → `complete` so the anon session/XSRF cookies
persist; keep it open as an async context manager.
"""

from __future__ import annotations

from typing import Any

from claude_ai.client import ClaudeAIClient
from claude_ai.config import ClaudeAISettings
from claude_ai.enums.auth import CredentialMethod, Locale, SourceApp
from claude_ai.login.errors import LoginError
from claude_ai.login.link import encode_email, parse_magic_link
from claude_ai.login.result import LoginResult
from claude_ai.models.auth import MagicLinkResult
from claude_ai.session.http import HttpSession


def _extract_org_uuid(account: dict[str, Any] | None) -> str | None:
    if not account:
        return None
    for membership in account.get("memberships") or []:
        organization = (membership or {}).get("organization") or {}
        uuid = organization.get("uuid")
        if uuid:
            return str(uuid)
    return None


class MagicLinkLogin:
    def __init__(
        self,
        *,
        settings: ClaudeAISettings | None = None,
        client: ClaudeAIClient | None = None,
    ) -> None:
        if client is not None:
            self._client = client
        else:
            session = HttpSession(account_id="login", settings=settings)
            self._client = ClaudeAIClient(
                account_id="login", session=session, settings=settings
            )
        self._email: str | None = None

    @property
    def client(self) -> ClaudeAIClient:
        return self._client

    async def open(self) -> None:
        await self._client.open()

    async def close(self) -> None:
        await self._client.close()

    async def __aenter__(self) -> MagicLinkLogin:
        await self.open()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def request(
        self,
        email: str,
        *,
        locale: Locale = Locale.EN_US,
        source: SourceApp = SourceApp.CLAUDE,
        utc_offset: int = 0,
    ) -> MagicLinkResult:
        self._email = email
        return await self._client.send_magic_link(
            email_address=email, locale=locale, source=source, utc_offset=utc_offset
        )

    async def complete(
        self,
        link_or_code: str,
        *,
        email: str | None = None,
        locale: Locale = Locale.EN_US,
        source: SourceApp = SourceApp.CLAUDE,
    ) -> LoginResult:
        parsed = parse_magic_link(link_or_code)
        resolved_email = email or self._email
        encoded = parsed.encoded_email or (
            encode_email(resolved_email) if resolved_email else None
        )
        if encoded is None:
            raise LoginError(
                "email is required to verify the magic link — pass email= or call request() first"
            )

        if parsed.is_code:
            result = await self._client.verify_magic_link(
                method=CredentialMethod.CODE,
                code=parsed.code,
                encoded_email_address=encoded,
                locale=locale,
                source=source,
            )
        elif parsed.nonce:
            result = await self._client.verify_magic_link(
                method=CredentialMethod.NONCE,
                nonce=parsed.nonce,
                encoded_email_address=encoded,
                locale=locale,
                source=source,
            )
        else:
            raise LoginError("could not extract a nonce or code from the magic link")

        if not result.success:
            raise LoginError("magic-link verification was not successful")

        org_uuid = _extract_org_uuid(result.account)
        if org_uuid:
            self._client.org_uuid = org_uuid

        cookies = dict(getattr(self._client.session, "cookies", {}) or {})
        return LoginResult(
            email=resolved_email or "",
            cookies=cookies,
            org_uuid=org_uuid,
            account=result.account,
            secret=result.secret,
        )
