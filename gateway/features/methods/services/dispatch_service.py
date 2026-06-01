"""MethodDispatchService: run any SDK method on a chosen account's client.

One path for all ~69 methods: validate name + params via the registry, resolve the
account's client, execute. Stream methods (``is_stream``) yield raw events for SSE;
everything else returns a JSON-serializable result.
"""

from __future__ import annotations

import base64
from collections.abc import AsyncIterator
from typing import Any

from pydantic import BaseModel

from claude_ai.orchestrator import ClaudeOrchestrator
from gateway.base.service import BaseService
from gateway.features.methods.errors import MethodParamsInvalid
from gateway.features.methods.registry import MethodRegistry
from gateway.shared.accounts import resolve_client


def _serialize(result: Any) -> Any:
    if result is None:
        return None
    if isinstance(result, BaseModel):
        return result.model_dump(mode="json")
    if isinstance(result, (list, tuple)):
        return [_serialize(item) for item in result]
    if isinstance(result, bytes):
        return {"_bytes_base64": base64.b64encode(result).decode()}
    return result


class MethodDispatchService(BaseService):
    def __init__(self, registry: MethodRegistry, orchestrator: ClaudeOrchestrator) -> None:
        self._registry = registry
        self._orch = orchestrator

    async def invoke(self, name: str, account_id: str, params: dict[str, Any]) -> Any:
        spec = self._registry.get(name)  # raises UnknownMethod
        if spec.is_stream:
            raise MethodParamsInvalid(f"{name} streams — call with stream=true")
        client = await resolve_client(self._orch, account_id)
        method, method_params = self._registry.build_instance(
            name, params, org_uuid=client.org_uuid or None
        )
        result = (
            await client(method)
            if method_params is None
            else await client(method, method_params)
        )
        return _serialize(result)

    async def invoke_stream(
        self, name: str, account_id: str, params: dict[str, Any]
    ) -> AsyncIterator[dict[str, Any]]:
        client = await resolve_client(self._orch, account_id)
        method, method_params = self._registry.build_instance(
            name, params, org_uuid=client.org_uuid or None
        )
        agen = await (
            client(method) if method_params is None else client(method, method_params)
        )
        async for event in agen:
            yield event.model_dump(mode="json") if isinstance(event, BaseModel) else {"raw": event}
