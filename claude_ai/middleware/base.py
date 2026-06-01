"""Generic Middleware[E,R] protocol + MiddlewareChain. Aiogram-style (handler, event, data) signature, reused for HTTP / stream / event-bus."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any, Generic, TypeVar

E = TypeVar("E")
R = TypeVar("R")

NextHandler = Callable[[E, dict[str, Any]], Awaitable[R]]


class Middleware(ABC, Generic[E, R]):
    @abstractmethod
    async def __call__(
        self,
        handler: NextHandler[E, R],
        event: E,
        data: dict[str, Any],
    ) -> R: ...


class MiddlewareChain(Generic[E, R]):
    def __init__(
        self,
        middlewares: list[Middleware[E, R]],
        terminal: NextHandler[E, R],
    ) -> None:
        self._chain = self._build(middlewares, terminal)

    @staticmethod
    def _build(
        middlewares: list[Middleware[E, R]],
        terminal: NextHandler[E, R],
    ) -> NextHandler[E, R]:
        chain = terminal
        for mw in reversed(middlewares):
            chain = _wrap(mw, chain)
        return chain

    async def __call__(self, event: E, data: dict[str, Any] | None = None) -> R:
        return await self._chain(event, data if data is not None else {})


def _wrap(mw: Middleware[E, R], nxt: NextHandler[E, R]) -> NextHandler[E, R]:
    async def wrapped(event: E, data: dict[str, Any]) -> R:
        return await mw(nxt, event, data)

    return wrapped
