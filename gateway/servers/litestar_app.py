"""Litestar adapter — high-throughput typed tier. Lazy-imports litestar inside the factory."""

from __future__ import annotations

from typing import Any

from gateway.servers.dispatch import lower_headers, run_route
from gateway.servers.handlers import GatewayHandlers
from gateway.servers.openapi import build_openapi, scalar_html
from gateway.servers.routes import ROUTES
from gateway.shared.container import AppContainer


def create_litestar_app(container: AppContainer) -> Any:
    from litestar import Litestar, MediaType, Request, Response
    from litestar.handlers import HTTPRouteHandler
    from litestar.response import Stream

    handlers = GatewayHandlers(container)
    spec = build_openapi(ROUTES)
    reference_html = scalar_html("/openapi.json")

    async def _openapi_json(_request: Request) -> Any:
        return Response(spec, media_type=MediaType.JSON)

    async def _scalar(_request: Request) -> Any:
        return Response(reference_html, media_type=MediaType.HTML)

    docs_handlers = [
        HTTPRouteHandler(path="/openapi.json", http_method="GET")(_openapi_json),
        *(
            HTTPRouteHandler(path=p, http_method="GET")(_scalar)
            for p in ("/docs", "/scalar")
        ),
    ]

    async def _on_startup(_app: Any) -> None:
        await container.open()

    async def _on_shutdown(_app: Any) -> None:
        await container.close()

    def make(route: Any) -> Any:
        async def fn(request: Request) -> Any:
            json_body: dict[str, Any] = {}
            if route.http in ("POST", "PATCH", "PUT"):
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
        route_handlers=[make(route) for route in ROUTES] + docs_handlers,
        on_startup=[_on_startup],
        on_shutdown=[_on_shutdown],
    )
