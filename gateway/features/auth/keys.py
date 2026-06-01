"""API-key minting + hashing.

Keys are high-entropy random tokens (``sk-`` + ``token_urlsafe(32)``), so a plain
SHA-256 of the key is a sufficient at-rest representation — bcrypt/argon2 target
low-entropy passwords, not 256-bit randoms. Lookups hash the inbound key and compare
in constant time. The plaintext is shown exactly once, at creation.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

KEY_PREFIX = "sk-"


def generate_key() -> tuple[str, str]:
    """Return ``(plaintext, sha256_hex)``. Persist only the hash."""
    raw = KEY_PREFIX + secrets.token_urlsafe(32)
    return raw, hash_key(raw)


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def verify(raw: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_key(raw), stored_hash)
