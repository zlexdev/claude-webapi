"""Framework-agnostic request/response contract shared by all server adapters."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from gateway.shared.principal import Principal


class RouteAuth(StrEnum):
    NONE = "none"
    KEY = "key"
    ADMIN = "admin"


@dataclass(slots=True)
class RequestContext:
    path_params: dict[str, str] = field(default_factory=dict)
    query: dict[str, str] = field(default_factory=dict)
    json_body: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    principal: Principal | None = None

    def header(self, name: str) -> str | None:
        return self.headers.get(name.lower())

    def need_principal(self) -> Principal:
        if self.principal is None:  # pragma: no cover - adapter guarantees it on KEY routes
            raise RuntimeError("principal missing on an authenticated route")
        return self.principal


@dataclass(slots=True)
class JsonResult:
    status: int
    body: dict[str, Any] | BaseModel


@dataclass(slots=True)
class StreamResult:
    lines: AsyncIterator[str]
    status: int = 200
    media_type: str = "text/event-stream"


HandlerResult = JsonResult | StreamResult


@dataclass(frozen=True, slots=True)
class QueryParam:
    name: str
    schema_type: str = "string"  # JSON-schema primitive type
    required: bool = False
    description: str | None = None


@dataclass(frozen=True, slots=True)
class RouteDef:
    http: str  # "GET" | "POST"
    path: str  # canonical, with {id} params
    handler: str  # GatewayHandlers method name
    auth: RouteAuth
    # OpenAPI contract (docs only — runtime dispatch reads the body manually).
    request_model: type[BaseModel] | None = None
    response_model: type[BaseModel] | None = None
    query: tuple[QueryParam, ...] = ()
    summary: str | None = None
