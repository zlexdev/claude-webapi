"""aiohttp adapter — lowest-overhead raw-throughput tier. Lazy-imports aiohttp."""

from __future__ import annotations

from typing import Any

from gateway.servers.dispatch import lower_headers, run_route
from gateway.servers.handlers import GatewayHandlers
from gateway.servers.openapi import build_openapi, scalar_html
from gateway.servers.routes import ROUTES
from gateway.shared.container import AppContainer


def create_aiohttp_app(container: AppContainer) -> Any:
    from aiohttp import web

    handlers = GatewayHandlers(container)
    spec = build_openapi(ROUTES)
    reference_html = scalar_html("/openapi.json")

    async def openapi_json(_request: Any) -> Any:
        return web.json_response(spec)

    async def scalar_reference(_request: Any) -> Any:
        return web.Response(text=reference_html, content_type="text/html")

    async def _on_startup(_app: Any) -> None:
        await container.open()

    async def _on_cleanup(_app: Any) -> None:
        await container.close()

    app = web.Application()
    app.on_startup.append(_on_startup)
    app.on_cleanup.append(_on_cleanup)

    def make(route: Any) -> Any:
        async def handler(request: Any) -> Any:
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
                path_params=dict(request.match_info),
                query=dict(request.query),
                json_body=json_body or {},
                headers=lower_headers(request.headers.items()),
            )
            if outcome.stream is not None:
                response = web.StreamResponse(
                    status=outcome.status, headers={"Content-Type": outcome.media_type}
                )
                await response.prepare(request)
                async for line in outcome.stream:
                    await response.write(line.encode())
                await response.write_eof()
                return response
            return web.json_response(outcome.json, status=outcome.status)

        return handler

    for route in ROUTES:
        app.router.add_route(route.http, route.path, make(route))
    app.router.add_get("/openapi.json", openapi_json)
    for docs_path in ("/docs", "/scalar"):
        app.router.add_get(docs_path, scalar_reference)
    return app
