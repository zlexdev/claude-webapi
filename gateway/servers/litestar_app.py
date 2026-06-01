"""Litestar adapter — high-throughput typed tier. Lazy-imports litestar inside the factory."""

from __future__ import annotations

from typing import Any

from gateway.servers.dispatch import lower_headers, run_route
from gateway.servers.handlers import GatewayHandlers
from gateway.servers.routes import ROUTES
from gateway.shared.container import AppContainer


def create_litestar_app(container: AppContainer) -> Any:
    from litestar import Litestar, Request, Response
    from litestar.handlers import HTTPRouteHandler
    from litestar.response import Stream

    handlers = GatewayHandlers(container)

    async def _on_startup(_app: Any) -> None:
        await container.open()

    async def _on_shutdown(_app: Any) -> None:
        await container.close()

    def make(route: Any) -> Any:
        async def fn(request: Request) -> Any:
            json_body: dict[str, Any] = {}
            if route.http == "POST":
                try:
                    json_body = await request.json()
                except Exception:  # noqa: BLE001 - empty/invalid body becomes {}
                    json_body = {}
            outcome = await run_route(
                container,
                handlers,
                route,
                path_params={k: str(v) for k, v in request.path_params.items()},
                query={k: request.query_params.get(k) for k in request.query_params},
                json_body=json_body or {},
                headers=lower_headers(request.headers.items()),
            )
            if outcome.stream is not None:
                return Stream(
                    outcome.stream, media_type=outcome.media_type, status_code=outcome.status
                )
            return Response(outcome.json, status_code=outcome.status, media_type="application/json")

        # Litestar uses {id:str} path-param syntax.
        path = route.path.replace("{id}", "{id:str}")
        return HTTPRouteHandler(path=path, http_method=route.http)(fn)

    return Litestar(
        route_handlers=[make(route) for route in ROUTES],
        on_startup=[_on_startup],
        on_shutdown=[_on_shutdown],
    )
