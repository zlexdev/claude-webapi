"""CookieCipher: Fernet at-rest encryption for account cookie jars.

The :class:`Account` DTO carries cookies as a plaintext ``dict`` in memory; this seals
them into a single Fernet token before they reach the Postgres ``data`` JSONB and unseals
on read. The stored ``cookies`` field is therefore a ``str`` token when a key is
configured, or a plain ``dict`` when it is not — so a pool provisioned before a key was
set keeps loading (legacy dicts pass straight through) and re-saving an account migrates
it to ciphertext. ``cryptography`` is imported lazily so the no-key / memory path never
pulls it in.
"""

from __future__ import annotations

import json

from gateway.features.auth.errors import CookieDecryptError


class CookieCipher:
    """Symmetric seal/unseal of a cookie jar with a urlsafe-base64 Fernet key."""

    def __init__(self, key: str) -> None:
        # cryptography is a heavy gateway-only optional dep — load it lazily so the
        # no-key / memory path never imports it.
        from cryptography.fernet import Fernet

        self._fernet = Fernet(key.encode())

    def encrypt(self, cookies: dict[str, str]) -> str:
        raw = json.dumps(cookies, separators=(",", ":")).encode()
        return self._fernet.encrypt(raw).decode()

    def decrypt(self, token: str) -> dict[str, str]:
        from cryptography.fernet import InvalidToken

        try:
            raw = self._fernet.decrypt(token.encode())
        except InvalidToken as exc:
            raise CookieDecryptError(
                "stored cookies could not be decrypted — wrong COOKIE_ENCRYPTION_KEY?"
            ) from exc
        data = json.loads(raw.decode())
        return {str(k): str(v) for k, v in data.items()}
