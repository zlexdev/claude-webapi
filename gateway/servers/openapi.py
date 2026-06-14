"""Framework-agnostic OpenAPI 3.1 spec built from ``ROUTES`` + their bound models.

FastAPI's auto-generated spec is empty here because every route is registered with one
untyped passthrough handler (no typed body param, ``-> Any`` return), so there is
nothing to introspect. We instead derive the spec from each ``RouteDef``'s
``request_model`` / ``response_model`` / ``query`` — pydantic emits the JSON schemas,
we wire them into ``components`` + per-operation ``requestBody`` / ``responses``.

This builder is adapter-agnostic: all three servers serve the same ``/openapi.json``
and the same Scalar reference HTML, so docs parity matches behavioural parity.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel
from pydantic.json_schema import models_json_schema

from gateway.features.completion.schemas.openai import OpenAIErrorEnvelope
from gateway.servers.context import QueryParam, RouteAuth, RouteDef

_PATH_PARAM = re.compile(r"\{(\w+)\}")

_SECURITY_SCHEMES: dict[str, dict[str, Any]] = {
    "ApiKey": {"type": "http", "scheme": "bearer", "bearerFormat": "sk-..."},
    "AdminToken": {"type": "apiKey", "in": "header", "name": "X-Admin-Token"},
}

_SECURITY_BY_AUTH: dict[RouteAuth, list[dict[str, list[str]]]] = {
    RouteAuth.KEY: [{"ApiKey": []}],
    RouteAuth.ADMIN: [{"AdminToken": []}],
}


def scalar_html(openapi_url: str = "/openapi.json", title: str = "claude-gateway API") -> str:
    """Minimal Scalar API-reference page pointed at ``openapi_url``."""
    return (
        f"<!doctype html><html><head><title>{title}</title>"
        '<meta charset="utf-8"/>'
        '<meta name="viewport" content="width=device-width, initial-scale=1"/></head>'
        f'<body><script id="api-reference" data-url="{openapi_url}"></script>'
        '<script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>'
        "</body></html>"
    )


def _tag(path: str) -> str:
    if path.startswith("/system"):
        return "System"
    if path.startswith("/v1/chats"):
        return "Chats"
    if path.startswith("/v1/methods"):
        return "Methods"
    if path == "/health":
        return "Health"
    return "Completion"


def _collect_models(routes: list[RouteDef]) -> list[type[BaseModel]]:
    models: list[type[BaseModel]] = [OpenAIErrorEnvelope]
    for route in routes:
        if route.request_model is not None:
            models.append(route.request_model)
        if route.response_model is not None:
            models.append(route.response_model)
    return list(dict.fromkeys(models))


def _path_parameters(path: str) -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "in": "path",
            "required": True,
            "schema": {"type": "string"},
        }
        for name in _PATH_PARAM.findall(path)
    ]


def _query_parameters(query: tuple[QueryParam, ...]) -> list[dict[str, Any]]:
    params: list[dict[str, Any]] = []
    for q in query:
        param: dict[str, Any] = {
            "name": q.name,
            "in": "query",
            "required": q.required,
            "schema": {"type": q.schema_type},
        }
        if q.description:
            param["description"] = q.description
        params.append(param)
    return params


def _responses(route: RouteDef, ref_for: dict[type[BaseModel], str]) -> dict[str, Any]:
    if route.response_model is not None:
        success: dict[str, Any] = {
            "description": "Successful Response",
            "content": {
                "application/json": {"schema": {"$ref": ref_for[route.response_model]}}
            },
        }
    else:
        success = {"description": "Successful Response"}
    responses: dict[str, Any] = {"200": success}
    if route.auth is not RouteAuth.NONE:
        responses["default"] = {
            "description": "Error",
            "content": {
                "application/json": {"schema": {"$ref": ref_for[OpenAIErrorEnvelope]}}
            },
        }
    return responses


def _operation(route: RouteDef, ref_for: dict[type[BaseModel], str]) -> dict[str, Any]:
    operation: dict[str, Any] = {
        "tags": [_tag(route.path)],
        "operationId": route.handler,
        "responses": _responses(route, ref_for),
    }
    if route.summary:
        operation["summary"] = route.summary
    parameters = _path_parameters(route.path) + _query_parameters(route.query)
    if parameters:
        operation["parameters"] = parameters
    if route.request_model is not None:
        operation["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {"schema": {"$ref": ref_for[route.request_model]}}
            },
        }
    security = _SECURITY_BY_AUTH.get(route.auth)
    if security is not None:
        operation["security"] = security
    return operation


def build_openapi(
    routes: list[RouteDef], *, title: str = "claude-gateway", version: str = "1.0.0"
) -> dict[str, Any]:
    models = _collect_models(routes)
    key_map, top = models_json_schema(
        [(m, "validation") for m in models],
        ref_template="#/components/schemas/{model}",
    )
    schemas: dict[str, Any] = top.get("$defs", {})
    ref_for: dict[type[BaseModel], str] = {
        m: key_map[(m, "validation")]["$ref"] for m in models
    }

    paths: dict[str, dict[str, Any]] = {}
    for route in routes:
        paths.setdefault(route.path, {})[route.http.lower()] = _operation(route, ref_for)

    return {
        "openapi": "3.1.0",
        "info": {"title": title, "version": version},
        "paths": paths,
        "components": {
            "schemas": schemas,
            "securitySchemes": _SECURITY_SCHEMES,
        },
    }
