"""MiddlewareManager + MiddlewareRegistry: scoped containers that build chains on demand."""

from __future__ import annotations

from collections.abc import Hashable
from typing import Any, Generic, TypeVar

from claude_ai.middleware.base import Middleware, MiddlewareChain, NextHandler

E = TypeVar("E")
R = TypeVar("R")


class MiddlewareManager(Generic[E, R]):
    def __init__(self, scope: Hashable = "default") -> None:
        self.scope = scope
        self._stack: list[Middleware[E, R]] = []

    def __len__(self) -> int:
        return len(self._stack)

    def use(self, middleware: Middleware[E, R]) -> Middleware[E, R]:
        self._stack.append(middleware)
        return middleware

    def insert(self, index: int, middleware: Middleware[E, R]) -> Middleware[E, R]:
        self._stack.insert(index, middleware)
        return middleware

    def remove(self, middleware: Middleware[E, R]) -> bool:
        try:
            self._stack.remove(middleware)
            return True
        except ValueError:
            return False

    def clear(self) -> None:
        self._stack.clear()

    def chain(self, terminal: NextHandler[E, R]) -> MiddlewareChain[E, R]:
        return MiddlewareChain(list(self._stack), terminal)

    async def __call__(
        self,
        terminal: NextHandler[E, R],
        event: E,
        data: dict[str, Any] | None = None,
    ) -> R:
        return await self.chain(terminal)(event, data)


class MiddlewareRegistry:
    def __init__(self) -> None:
        self._scopes: dict[Hashable, MiddlewareManager[Any, Any]] = {}

    def get(self, scope: Hashable) -> MiddlewareManager[Any, Any]:
        manager = self._scopes.get(scope)
        if manager is None:
            manager = MiddlewareManager(scope=scope)
            self._scopes[scope] = manager
        return manager

    def http(self) -> MiddlewareManager[Any, Any]:
        return self.get("http")

    def stream(self) -> MiddlewareManager[Any, Any]:
        return self.get("stream")

    def events(self) -> MiddlewareManager[Any, Any]:
        return self.get("events")

    def clear(self, scope: Hashable | None = None) -> None:
        if scope is None:
            for manager in self._scopes.values():
                manager.clear()
            return
        existing = self._scopes.get(scope)
        if existing is not None:
            existing.clear()
