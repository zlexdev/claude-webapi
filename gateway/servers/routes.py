"""ROUTES — the single source of truth for the gateway's HTTP surface.

Each adapter iterates this list. OpenAI paths (`/v1/chat/completions`, `/v1/models`)
are kept verbatim as an external contract; gateway-native paths follow POST/GET +
verb-in-path (D16). ``{id}`` is the canonical path-param syntax; adapters translate.
"""

from __future__ import annotations

from gateway.servers.context import RouteAuth, RouteDef

ROUTES: list[RouteDef] = [
    RouteDef("GET", "/health", "health", RouteAuth.NONE),
    # OpenAI-compatible surface (external contract, verbatim)
    RouteDef("POST", "/v1/chat/completions", "chat_completions", RouteAuth.KEY),
    RouteDef("GET", "/v1/models", "models_list", RouteAuth.KEY),
    # Simple text endpoint
    RouteDef("POST", "/v1/prompt", "prompt", RouteAuth.KEY),
    # Chat management
    RouteDef("GET", "/v1/chats/list", "chats_list", RouteAuth.KEY),
    RouteDef("POST", "/v1/chats/create", "chats_create", RouteAuth.KEY),
    RouteDef("GET", "/v1/chats/{id}/messages", "chat_messages", RouteAuth.KEY),
    RouteDef("POST", "/v1/chats/{id}/send", "chat_send", RouteAuth.KEY),
    # Generic SDK method dispatch + auto-docs
    RouteDef("GET", "/v1/methods/list", "methods_list", RouteAuth.KEY),
    RouteDef("POST", "/v1/methods/invoke", "methods_invoke", RouteAuth.KEY),
    # System / admin
    RouteDef("POST", "/system/accounts/create", "system_account_create", RouteAuth.ADMIN),
    RouteDef("GET", "/system/accounts/list", "system_account_list", RouteAuth.ADMIN),
    RouteDef(
        "PATCH", "/system/accounts/{id}/cookies", "system_account_update", RouteAuth.ADMIN
    ),
    RouteDef("POST", "/system/keys/generate", "system_key_generate", RouteAuth.ADMIN),
    RouteDef("GET", "/system/keys/list", "system_key_list", RouteAuth.ADMIN),
    RouteDef("POST", "/system/keys/revoke", "system_key_revoke", RouteAuth.ADMIN),
]
