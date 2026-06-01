"""Regression: the real FastAPI ASGI app must route GET requests, not 422 them.

The handler-level tests (test_routes_handlers) never exercise the actual FastAPI
adapter, so a bug where `from __future__ import annotations` stringized the
`request: Request` parameter — making FastAPI treat `request` as a required query
param and return 422 on every GET (including /health) — slipped through. This test
drives the app via Starlette's TestClient to lock that fix.
"""

from __future__ import annotations

from typing import Any

from starlette.testclient import TestClient

from gateway.servers.fastapi_app import create_fastapi_app
from gateway.shared.config import GatewaySettings
from gateway.shared.container import AppContainer


class _Orch:
    """Minimal orchestrator stub — /health and unauthenticated /v1/models never
    resolve an account, so the pool surface is all that's needed to open/close."""

    @property
    def bus(self) -> None:
        return None

    async def start(self) -> None: ...
    async def add(self, client: Any, *, tier: Any = None) -> None: ...
    async def get(self, account_id: str) -> Any:
        raise KeyError(account_id)

    async def close(self) -> None: ...


def _client() -> TestClient:
    settings = GatewaySettings(admin_token="admintok", db="memory")
    container = AppContainer(settings, orchestrator=_Orch())
    return TestClient(create_fastapi_app(container))


def test_health_get_returns_200_not_422() -> None:
    with _client() as client:
        r = client.get("/health")
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "ok"


def test_models_get_is_auth_gated_not_validation_422() -> None:
    # Without a key /v1/models must be 401 (auth) — never 422 (the old GET bug).
    with _client() as client:
        r = client.get("/v1/models")
        assert r.status_code == 401, r.text
        assert r.status_code != 422


def test_docs_serve_scalar_not_swagger() -> None:
    with _client() as client:
        r = client.get("/docs")
        assert r.status_code == 200, r.text
        assert "@scalar/api-reference" in r.text
        assert "swagger-ui" not in r.text.lower()
        assert client.get("/openapi.json").status_code == 200
