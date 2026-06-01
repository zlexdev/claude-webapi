"""Errors for the generic method-dispatch feature."""

from __future__ import annotations

from gateway.base.errors import GatewayError


class UnknownMethod(GatewayError):
    status_code = 400
    error_type = "invalid_request_error"
    message = "Unknown method"


class MethodParamsInvalid(GatewayError):
    status_code = 422
    error_type = "invalid_request_error"
    message = "Invalid params for method"


class MultipartNotSupported(GatewayError):
    status_code = 400
    error_type = "invalid_request_error"
    message = "Multipart methods are not callable via generic dispatch — use the dedicated endpoint"
