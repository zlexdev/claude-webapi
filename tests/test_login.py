"""Tests for the magic-link login flow (claude_ai/login)."""

from __future__ import annotations

from typing import Any

import pytest

from claude_ai.enums.auth import CredentialMethod
from claude_ai.login.errors import LoginError
from claude_ai.login.link import encode_email, parse_magic_link
from claude_ai.login.session import MagicLinkLogin, _extract_org_uuid
from claude_ai.models.auth import AuthResult, MagicLinkResult


def test_encode_email_matches_observed_sample() -> None:
    assert encode_email("trakalyukirinairina@gmail.com") == "dHJha2FseXVraXJpbmFpcmluYUBnbWFpbC5jb20="


def test_parse_magic_link_shapes() -> None:
    enc = encode_email("a@b.com")
    p = parse_magic_link(f"https://claude.ai/magic-link/{enc}/abc123nonce")
    assert p.nonce == "abc123nonce" and p.encoded_email == enc
    assert parse_magic_link("https://claude.ai/magic-link?nonce=XYZ").nonce == "XYZ"
    assert parse_magic_link("https://claude.ai/magic-link#code=NPC").nonce == "NPC"
    assert parse_magic_link("barenonce123").nonce == "barenonce123"
    code = parse_magic_link("482913")
    assert code.is_code and code.code == "482913"


def test_extract_org_uuid() -> None:
    assert _extract_org_uuid({"memberships": [{"organization": {"uuid": "org-9"}}]}) == "org-9"
    assert _extract_org_uuid({}) is None
    assert _extract_org_uuid(None) is None


class _FakeSession:
    def __init__(self) -> None:
        self.cookies: dict[str, str] = {}


class _FakeClient:
    def __init__(self) -> None:
        self.session = _FakeSession()
        self.org_uuid = ""
        self.calls: list[Any] = []

    async def open(self) -> None: ...
    async def close(self) -> None: ...

    async def send_magic_link(self, email_address: str, **_: Any) -> MagicLinkResult:
        self.calls.append(("send", email_address))
        return MagicLinkResult(sent=True)

    async def verify_magic_link(self, **kw: Any) -> AuthResult:
        self.calls.append(("verify", kw))
        self.session.cookies = {"sessionKey": "sk-ant-sid", "XSRF-TOKEN": "xt"}
        return AuthResult(
            success=True,
            secret="act-secret",
            account={"memberships": [{"organization": {"uuid": "org-42"}}]},
        )


async def test_complete_with_link_returns_cookies_and_org() -> None:
    fake = _FakeClient()
    async with MagicLinkLogin(client=fake) as login:  # type: ignore[arg-type]
        await login.request("user@example.com")
        link = f"https://claude.ai/magic-link/{encode_email('user@example.com')}/NONCE123"
        result = await login.complete(link)
    assert result.cookies == {"sessionKey": "sk-ant-sid", "XSRF-TOKEN": "xt"}
    assert result.org_uuid == "org-42" and fake.org_uuid == "org-42"
    assert result.secret == "act-secret" and result.email == "user@example.com"
    verify_kwargs = fake.calls[1][1]
    assert verify_kwargs["nonce"] == "NONCE123"
    assert verify_kwargs["encoded_email_address"] == encode_email("user@example.com")
    assert verify_kwargs["method"] is CredentialMethod.NONCE


async def test_complete_with_numeric_code() -> None:
    fake = _FakeClient()
    async with MagicLinkLogin(client=fake) as login:  # type: ignore[arg-type]
        await login.request("a@b.com")
        await login.complete("482913")
    verify_kwargs = fake.calls[1][1]
    assert verify_kwargs["code"] == "482913" and verify_kwargs["method"] is CredentialMethod.CODE


async def test_failed_verification_raises() -> None:
    class _Fail(_FakeClient):
        async def verify_magic_link(self, **kw: Any) -> AuthResult:
            return AuthResult(success=False)

    async with MagicLinkLogin(client=_Fail()) as login:  # type: ignore[arg-type]
        with pytest.raises(LoginError):
            await login.complete("NONCE", email="x@y.com")


async def test_missing_email_raises() -> None:
    async with MagicLinkLogin(client=_FakeClient()) as login:  # type: ignore[arg-type]
        with pytest.raises(LoginError):
            await login.complete("NONCE")
