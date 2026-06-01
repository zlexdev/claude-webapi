"""Completion-feature errors."""

from __future__ import annotations

from gateway.base.errors import GatewayError


class NoMessages(GatewayError):
    status_code = 400
    error_type = "invalid_request_error"
    message = "Request contains no usable message text"
