"""AppContainer: the DI root. Builds stores, orchestrator, and all services; owns lifecycle.

Built once per process inside the chosen server's lifespan (everything is loop-bound, A3).
Postgres backends + SQLAlchemy are imported lazily only when ``db=postgres`` so the
memory path and the rest of the gateway import without SQLAlchemy/asyncpg installed.
"""

from __future__ import annotations

import asyncio
import hmac
from collections.abc import Coroutine
from typing import TYPE_CHECKING, Any

from claude_ai.orchestrator import ClaudeOrchestrator
from gateway.features.auth.errors import AdminForbidden
from gateway.shared.principal import Principal
from gateway.shared.rate_limit import RateLimited
from gateway.features.auth.services.account_service import AccountService
from gateway.features.auth.services.apikey_service import ApiKeyService
from gateway.features.auth.store.base import BaseAccountStore, BaseApiKeyStore
from gateway.features.auth.store.memory import MemoryAccountStore, MemoryApiKeyStore
from gateway.features.chats.services.chat_service import ChatService
from gateway.features.completion.services.completion_service import CompletionService
from gateway.features.methods.registry import MethodRegistry
from gateway.features.methods.services.dispatch_service import MethodDispatchService
from gateway.features.methods.services.docgen_service import MethodDocGenerator
from gateway.features.models_map.services.model_mapper import ModelMapper
from gateway.shared.config import GatewaySettings
from gateway.shared.logging import configure_logging, get_logger
from gateway.shared.rate_limit import KeyedRateLimiter

if TYPE_CHECKING:
    from gateway.features.auth.cipher import CookieCipher
    from gateway.shared.db.engine import Database

log = get_logger("container")


class AppContainer:
    def __init__(
        self, settings: GatewaySettings, *, orchestrator: ClaudeOrchestrator | None = None
    ) -> None:
        self.settings = settings
        self._db: Database | None = None
        self._bg: set[asyncio.Task[Any]] = set()
        self.accounts: BaseAccountStore
        self.keys: BaseApiKeyStore
        self.orch = orchestrator if orchestrator is not None else ClaudeOrchestrator()
        self.registry = MethodRegistry()
        self.mapper = ModelMapper(settings.model_aliases, settings.default_model)
        self.rate_limiter = KeyedRateLimiter(settings.rate_limit_per_min)
        self._build_stores()
        self.account_service = AccountService(self.accounts, self.orch)
        self.apikey_service = ApiKeyService(self.keys, self.account_service)
        self.completion = CompletionService(
            self.orch, self.mapper, default_model=settings.default_model
        )
        self.chats = ChatService(self.orch)
        self.dispatch = MethodDispatchService(self.registry, self.orch)
        self.docgen = MethodDocGenerator(self.registry)

    def _build_stores(self) -> None:
        if self.settings.db == "memory":
            self.accounts = MemoryAccountStore()
            self.keys = MemoryApiKeyStore()
            return
        # Lazy heavy optional dep (SQLAlchemy + asyncpg) — only when db=postgres.
        from gateway.features.auth.store.postgres import (
            PostgresAccountStore,
            PostgresApiKeyStore,
        )
        from gateway.shared.db.engine import Database

        assert self.settings.database_url is not None  # guaranteed by settings validator
        self._db = Database(self.settings.database_url)
        self.accounts = PostgresAccountStore(self._db, cipher=self._build_cipher())
        self.keys = PostgresApiKeyStore(self._db)

    def _build_cipher(self) -> CookieCipher | None:
        """Fernet cookie cipher when a key is set; None leaves cookies plaintext at rest."""
        key = self.settings.cookie_encryption_key
        if not key:
            return None
        from gateway.features.auth.cipher import CookieCipher

        return CookieCipher(key)

    def schedule(self, coro: Coroutine[Any, Any, Any]) -> None:
        """Run a fire-and-forget coroutine, keeping a ref so it isn't GC'd."""
        task = asyncio.ensure_future(coro)
        self._bg.add(task)
        task.add_done_callback(self._bg.discard)

    async def authenticate(self, authorization: str | None) -> Principal:
        principal = await self.apikey_service.authenticate(authorization)
        if not self.rate_limiter.allow(principal.key_id):
            raise RateLimited()
        self.schedule(self.apikey_service.touch(principal.key_id))
        return principal

    def verify_admin(self, token: str | None) -> None:
        if not token or not hmac.compare_digest(token, self.settings.admin_token):
            raise AdminForbidden()

    async def open(self) -> None:
        configure_logging()
        if self._db is not None:
            await self._db.create_all()
        await self.orch.start()
        rehydrated = await self.account_service.rehydrate_all()
        log.info("container open", extra={"db": self.settings.db, "accounts": rehydrated})

    async def close(self) -> None:
        await self.orch.close()
        await self.keys.close()
        await self.accounts.close()
        if self._db is not None:
            await self._db.close()

    async def __aenter__(self) -> AppContainer:
        await self.open()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()
