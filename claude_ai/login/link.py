"""Parse a magic-link (URL, bare nonce, or numeric fallback code) into credentials.

The flow already knows the email, so the link only needs to yield the *nonce* — the
``encoded_email_address`` is derived from the email when the link doesn't carry it.
This keeps parsing robust to the exact email-link shape claude.ai uses.
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit

_NONCE_QUERY_KEYS = ("nonce", "code", "token")
_EMAIL_QUERY_KEYS = ("encoded_email_address", "email", "e")
_IGNORE_SEGMENTS = {
    "",
    "magic-link",
    "magic_link",
    "verify",
    "verify_magic_link",
    "login",
    "auth",
}


def encode_email(email: str) -> str:
    """Base64-encode an email the way claude.ai's ``encoded_email_address`` expects."""
    return base64.b64encode(email.strip().encode()).decode()


def _looks_like_encoded_email(segment: str) -> bool:
    try:
        decoded = base64.b64decode(segment + "=" * (-len(segment) % 4)).decode()
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return False
    return "@" in decoded


@dataclass(slots=True)
class ParsedLink:
    nonce: str | None = None
    code: str | None = None
    encoded_email: str | None = None

    @property
    def is_code(self) -> bool:
        return self.code is not None and self.nonce is None


def parse_magic_link(value: str) -> ParsedLink:
    raw = value.strip()
    if not raw:
        raise ValueError("empty magic link")

    if raw.isdigit():
        return ParsedLink(code=raw)

    if not any(ch in raw for ch in "://?#") and "/" not in raw:
        if _looks_like_encoded_email(raw):
            return ParsedLink(encoded_email=raw)
        return ParsedLink(nonce=raw)

    parts = urlsplit(raw)
    query = parse_qs(parts.query)
    fragment_query = parse_qs(parts.fragment)

    def pick(keys: tuple[str, ...]) -> str | None:
        for key in keys:
            for source in (query, fragment_query):
                if source.get(key):
                    return source[key][0]
        return None

    nonce = pick(_NONCE_QUERY_KEYS)
    encoded_email = pick(_EMAIL_QUERY_KEYS)

    segments = [
        seg
        for seg in (*parts.path.split("/"), *parts.fragment.split("/"))
        if seg and seg not in _IGNORE_SEGMENTS
    ]
    for seg in segments:
        if encoded_email is None and _looks_like_encoded_email(seg):
            encoded_email = seg
        elif nonce is None:
            nonce = seg

    if nonce is not None and nonce.isdigit():
        return ParsedLink(code=nonce, encoded_email=encoded_email)
    return ParsedLink(nonce=nonce, encoded_email=encoded_email)
