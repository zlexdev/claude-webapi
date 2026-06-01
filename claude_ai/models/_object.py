"""ClaudeObject: base for all pydantic models, supports .bind(client) for fluent calls."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, PrivateAttr

if TYPE_CHECKING:
    from claude_ai.client import ClaudeAIClient


class ClaudeObject(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    _client: ClaudeAIClient | None = PrivateAttr(default=None)

    def bind(self, client: ClaudeAIClient) -> ClaudeObject:
        self._client = client
        for value in self.__dict__.values():
            _bind_recursive(value, client)
        return self

    @property
    def client(self) -> ClaudeAIClient:
        if self._client is None:
            raise RuntimeError(
                "ClaudeObject not bound to a client. Call .bind(client) first "
                "or fetch via ClaudeAIClient methods which auto-bind."
            )
        return self._client


def _bind_recursive(obj: Any, client: ClaudeAIClient) -> None:
    if isinstance(obj, ClaudeObject):
        obj.bind(client)
    elif isinstance(obj, list):
        for item in obj:
            _bind_recursive(item, client)
    elif isinstance(obj, dict):
        for item in obj.values():
            _bind_recursive(item, client)
