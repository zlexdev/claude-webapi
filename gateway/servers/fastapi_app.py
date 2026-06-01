"""FastAPI adapter — balanced default tier. Lazy-imports fastapi inside the factory."""

# NOTE: no `from __future__ import annotations` here. FastAPI identifies the
# request parameter by its resolved `Request` type; with stringized annotations it
# would resolve `"Request"` against this module's globals (where fastapi is only
# imported locally inside the factory), fail, and treat `request` as a required
# query param — making every GET return 422. Real annotations avoid that.

from collections.abc import AsyncIterator
from typing import Any

from gateway.servers.dispatch import lower_headers, run_route
from gateway.servers.handlers import GatewayHandlers
from gateway.servers.routes import ROUTES
from gateway.shared.container import AppContainer


def create_fastapi_app(container: AppContainer) -> Any:
    from contextlib import asynccontextmanager

    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse, StreamingResponse

    handlers = GatewayHandlers(container)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        await container.open()
        try:
            yield
        finally:
            await container.close()

    app = FastAPI(title="claude-gateway", lifespan=lifespan)

    def register(route: Any) -> None:
        async def endpoint(request: Request) -> Any:
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
                path_params=dict(request.path_params),
                query=dict(request.query_params),
                json_body=json_body or {},
                headers=lower_headers(request.headers.items()),
            )
            if outcome.stream is not None:
                return StreamingResponse(
                    outcome.stream, media_type=outcome.media_type, status_code=outcome.status
                )
            return JSONResponse(outcome.json, status_code=outcome.status)

        app.add_api_route(route.path, endpoint, methods=[route.http], name=route.handler)

    for route in ROUTES:
        register(route)
    return app
