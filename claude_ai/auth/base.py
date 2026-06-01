"""BaseAuth: shared auth object — actually()/update()/subscribe(). Multiple sessions can share one instance and see each others' refreshes."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

AuthListener = Callable[["AuthSnapshot"], Awaitable[None] | None]


@dataclass(slots=True)
class AuthSnapshot:
    cookies: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    xsrf_token: str | None = None
    revision: int = 0


class BaseAuth(ABC):
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._listeners: list[AuthListener] = []

    @abstractmethod
    async def actually(self) -> AuthSnapshot: ...

    @abstractmethod
    async def update(
        self,
        cookies: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> AuthSnapshot: ...

    def subscribe(self, listener: AuthListener) -> Callable[[], None]:
        self._listeners.append(listener)

        def cancel() -> None:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

        return cancel

    async def _notify(self, snapshot: AuthSnapshot) -> None:
        for listener in list(self._listeners):
            result = listener(snapshot)
            if asyncio.iscoroutine(result):
                await result
