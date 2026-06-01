"""run_route: the shared per-request pipeline used by all three server adapters.

Centralizes auth (KEY/ADMIN), handler invocation, and exception → OpenAI-envelope
mapping, so each ``*_app`` only extracts native request fields and builds the native
response. This is why the three servers are behaviourally identical.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from gateway.servers.context import RequestContext, RouteAuth, RouteDef, StreamResult
from gateway.servers.handlers import GatewayHandlers
from gateway.shared.container import AppContainer
from gateway.shared.errors import map_exception


@dataclass(slots=True)
class Outcome:
    status: int
    json: dict[str, Any] | None
    stream: AsyncIterator[str] | None
    media_type: str


async def run_route(
    container: AppContainer,
    handlers: GatewayHandlers,
    route: RouteDef,
    *,
    path_params: dict[str, str],
    query: dict[str, str],
    json_body: dict[str, Any],
    headers: dict[str, str],
) -> Outcome:
    try:
        ctx = RequestContext(
            path_params=path_params, query=query, json_body=json_body, headers=headers
        )
        if route.auth is RouteAuth.KEY:
            ctx.principal = await container.authenticate(headers.get("authorization"))
        elif route.auth is RouteAuth.ADMIN:
            container.verify_admin(headers.get("x-admin-token"))
        result = await getattr(handlers, route.handler)(ctx)
        if isinstance(result, StreamResult):
            return Outcome(result.status, None, result.lines, result.media_type)
        payload = (
            result.body.model_dump(mode="json")
            if isinstance(result.body, BaseModel)
            else result.body
        )
        return Outcome(result.status, payload, None, "application/json")
    except Exception as exc:  # noqa: BLE001 - boundary: map every error to an OpenAI envelope
        mapped = map_exception(exc)
        return Outcome(mapped.status, mapped.payload, None, "application/json")


def lower_headers(items: object) -> dict[str, str]:
    """Normalize a headers iterable of (k, v) pairs to a lowercase dict."""
    result: dict[str, str] = {}
    for key, value in items:  # type: ignore[attr-defined]
        result[str(key).lower()] = str(value)
    return result
