"""Entry point: build the container and launch the configured server.

    python -m gateway                 # uses CLAUDE_GATEWAY_SERVER (default fastapi)
    python -m gateway --server aiohttp --port 8081
"""

from __future__ import annotations

import argparse
from typing import Any

from gateway.shared.config import GatewaySettings
from gateway.shared.container import AppContainer
from gateway.shared.logging import configure_logging, get_logger

log = get_logger("run")


def build_app(container: AppContainer) -> Any:
    server = container.settings.server
    if server == "fastapi":
        from gateway.servers.fastapi_app import create_fastapi_app

        return create_fastapi_app(container)
    if server == "litestar":
        from gateway.servers.litestar_app import create_litestar_app

        return create_litestar_app(container)
    from gateway.servers.aiohttp_app import create_aiohttp_app

    return create_aiohttp_app(container)


def _settings_from_cli() -> GatewaySettings:
    parser = argparse.ArgumentParser(prog="gateway")
    parser.add_argument("--server", choices=["fastapi", "litestar", "aiohttp"])
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    settings = GatewaySettings()
    overrides = {k: v for k, v in vars(args).items() if v is not None}
    return settings.model_copy(update=overrides) if overrides else settings


def main() -> None:
    configure_logging()
    settings = _settings_from_cli()
    container = AppContainer(settings)
    app = build_app(container)
    log.info("starting", extra={"server": settings.server, "host": settings.host, "port": settings.port})
    if settings.server == "aiohttp":
        from aiohttp import web

        web.run_app(app, host=settings.host, port=settings.port)
    else:
        import uvicorn

        uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
