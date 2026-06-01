"""ROUTES — the single source of truth for the gateway's HTTP surface + contract.

Each adapter iterates this list for routing; ``servers/openapi.py`` reads the bound
``request_model`` / ``response_model`` / ``query`` to build the OpenAPI spec. OpenAI
paths (`/v1/chat/completions`, `/v1/models`) are kept verbatim as an external contract;
gateway-native paths follow POST/GET + verb-in-path (D16). ``{id}`` is the canonical
path-param syntax; adapters translate.
"""

from __future__ import annotations

from gateway.features.auth.schemas.dtos import (
    AccountCreated,
    AccountInfo,
    CreateAccountRequest,
    GenerateKeyRequest,
    KeyGenerated,
    KeyInfo,
    KeyRevoked,
    RevokeKeyRequest,
)
from gateway.features.chats.schemas.dtos import (
    ChatSummary,
    CreateChatRequest,
    MessageDTO,
    SendToChatRequest,
)
from gateway.features.completion.schemas.dtos import TextPromptRequest, TextPromptResponse
from gateway.features.completion.schemas.openai import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ModelList,
)
from gateway.features.methods.schemas.dtos import (
    MethodInvokeRequest,
    MethodInvokeResult,
    MethodList,
)
from gateway.servers.context import QueryParam, RouteAuth, RouteDef
from gateway.shared.schemas.health import HealthResponse
from gateway.shared.schemas.pagination import Page

_LIMIT = QueryParam("limit", "integer", description="Page size (clamped 1..200).")
_CURSOR = QueryParam("cursor", description="Opaque keyset cursor from a prior page.")
_PAGE = (_LIMIT, _CURSOR)

ROUTES: list[RouteDef] = [
    RouteDef(
        "GET", "/health", "health", RouteAuth.NONE,
        response_model=HealthResponse, summary="Liveness probe.",
    ),
    # OpenAI-compatible surface (external contract, verbatim)
    RouteDef(
        "POST", "/v1/chat/completions", "chat_completions", RouteAuth.KEY,
        request_model=ChatCompletionRequest, response_model=ChatCompletionResponse,
        summary="OpenAI-compatible chat completion (stream or non-stream).",
    ),
    RouteDef(
        "GET", "/v1/models", "models_list", RouteAuth.KEY,
        response_model=ModelList, summary="List available model ids.",
    ),
    # Simple text endpoint
    RouteDef(
        "POST", "/v1/prompt", "prompt", RouteAuth.KEY,
        request_model=TextPromptRequest, response_model=TextPromptResponse,
        summary="Send one text prompt, get one text answer.",
    ),
    # Chat management
    RouteDef(
        "GET", "/v1/chats/list", "chats_list", RouteAuth.KEY,
        response_model=Page[ChatSummary], query=(_LIMIT,), summary="List chats.",
    ),
    RouteDef(
        "POST", "/v1/chats/create", "chats_create", RouteAuth.KEY,
        request_model=CreateChatRequest, response_model=ChatSummary,
        summary="Create a chat.",
    ),
    RouteDef(
        "GET", "/v1/chats/{id}/messages", "chat_messages", RouteAuth.KEY,
        response_model=Page[MessageDTO], query=_PAGE, summary="List messages in a chat.",
    ),
    RouteDef(
        "POST", "/v1/chats/{id}/send", "chat_send", RouteAuth.KEY,
        request_model=SendToChatRequest, response_model=ChatCompletionResponse,
        summary="Send a message to an existing chat (stream or non-stream).",
    ),
    # Generic SDK method dispatch + auto-docs
    RouteDef(
        "GET", "/v1/methods/list", "methods_list", RouteAuth.KEY,
        response_model=MethodList, summary="List all dispatchable SDK methods.",
    ),
    RouteDef(
        "POST", "/v1/methods/invoke", "methods_invoke", RouteAuth.KEY,
        request_model=MethodInvokeRequest, response_model=MethodInvokeResult,
        summary="Invoke any SDK method by name (params are method-specific).",
    ),
    # System / admin
    RouteDef(
        "POST", "/system/accounts/create", "system_account_create", RouteAuth.ADMIN,
        request_model=CreateAccountRequest, response_model=AccountCreated,
        summary="Provision an account from cookies.",
    ),
    RouteDef(
        "GET", "/system/accounts/list", "system_account_list", RouteAuth.ADMIN,
        response_model=Page[AccountInfo], query=_PAGE, summary="List accounts.",
    ),
    RouteDef(
        "POST", "/system/keys/generate", "system_key_generate", RouteAuth.ADMIN,
        request_model=GenerateKeyRequest, response_model=KeyGenerated,
        summary="Generate an API key (against an account or fresh cookies).",
    ),
    RouteDef(
        "GET", "/system/keys/list", "system_key_list", RouteAuth.ADMIN,
        response_model=Page[KeyInfo],
        query=(QueryParam("account_id", description="Filter by account."), _LIMIT, _CURSOR),
        summary="List API keys.",
    ),
    RouteDef(
        "POST", "/system/keys/revoke", "system_key_revoke", RouteAuth.ADMIN,
        request_model=RevokeKeyRequest, response_model=KeyRevoked,
        summary="Revoke an API key.",
    ),
]
