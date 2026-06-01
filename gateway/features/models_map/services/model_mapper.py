"""ModelMapper: alias -> claude id, with passthrough for real ids and a default fallback.

Returns plain model-id strings; the OpenAI ``/v1/models`` handler wraps them into the
wire DTOs (so this feature never imports the completion feature)."""

from __future__ import annotations

from gateway.base.service import BaseService
from gateway.features.models_map.registry import DEFAULT_ALIASES, KNOWN_CLAUDE


class ModelMapper(BaseService):
    def __init__(self, aliases: dict[str, str] | None = None, default_model: str = "claude-sonnet-4-6") -> None:
        self._aliases = {**DEFAULT_ALIASES, **(aliases or {})}
        self._default = default_model

    def resolve(self, name: str) -> str:
        if name in self._aliases:
            return self._aliases[name]
        if name in KNOWN_CLAUDE:
            return name
        return self._default

    def list_model_ids(self) -> list[str]:
        return sorted(set(self._aliases) | KNOWN_CLAUDE)
