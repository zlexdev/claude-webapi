"""Boundary error mapper: any exception -> (HTTP status, OpenAI error-envelope dict).

Lives in ``shared`` and emits a plain dict (the OpenAI wire shape) so it never imports
a feature package. Handles gateway errors, SDK errors, pydantic validation, and the
catch-all. The dict shape is ``{"error": {"message", "type", "code"}}``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from claude_ai.exceptions import APIError, ClaudeAIError
from gateway.base.errors import GatewayError
from gateway.shared.logging import get_logger

log = get_logger("errors")

# OpenAI error `type` by HTTP status.
_TYPE_BY_STATUS = {
    400: "invalid_request_error",
    401: "authentication_error",
    403: "permission_error",
    404: "not_found_error",
    409: "conflict_error",
    422: "invalid_request_error",
    429: "rate_limit_error",
}


@dataclass(frozen=True, slots=True)
class ErrorResponse:
    status: int
    payload: dict[str, Any]


def _envelope(message: str, type_: str, code: str | None) -> dict[str, Any]:
    return {"error": {"message": message, "type": type_, "code": code}}


def map_exception(exc: BaseException) -> ErrorResponse:
    if isinstance(exc, GatewayError):
        type_ = exc.error_type or _TYPE_BY_STATUS.get(exc.status_code, "api_error")
        return ErrorResponse(exc.status_code, _envelope(exc.message, type_, exc.code))

    if isinstance(exc, APIError):
        status = exc.status_code
        type_ = _TYPE_BY_STATUS.get(status, "api_error" if status < 500 else "server_error")
        return ErrorResponse(status, _envelope(str(exc), type_, None))

    if isinstance(exc, ValidationError):
        return ErrorResponse(422, _envelope(_first_validation_message(exc), "invalid_request_error", None))

    if isinstance(exc, ClaudeAIError):
        # network / stream / session — upstream is unreachable or misbehaving.
        return ErrorResponse(502, _envelope(str(exc) or "Upstream error", "api_error", "upstream_error"))

    log.exception("unhandled error mapped to 500")
    return ErrorResponse(500, _envelope("Internal server error", "server_error", None))


def _first_validation_message(exc: ValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "Invalid request"
    first = errors[0]
    loc = ".".join(str(p) for p in first.get("loc", ()))
    msg = first.get("msg", "invalid")
    return f"{loc}: {msg}" if loc else msg
