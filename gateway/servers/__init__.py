"""servers: three thin framework adapters (FastAPI / Litestar / aiohttp) over one core.

All endpoint logic lives in ``handlers.GatewayHandlers`` and the route map in
``routes.ROUTES``; each ``*_app`` module only adapts native request/response + SSE
framing. Framework imports are lazy (inside each ``create_*_app``) so this package
imports without the frameworks installed.
"""
