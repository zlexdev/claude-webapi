"""Auth-domain errors. Each carries its HTTP status + OpenAI error type via GatewayError."""

from __future__ import annotations

from gateway.base.errors import GatewayError


class MissingApiKey(GatewayError):
    status_code = 401
    error_type = "authentication_error"
    message = "Missing API key — send 'Authorization: Bearer sk-...'"


class InvalidApiKey(GatewayError):
    status_code = 401
    error_type = "authentication_error"
    message = "Invalid API key"


class RevokedApiKey(GatewayError):
    status_code = 401
    error_type = "authentication_error"
    message = "API key has been revoked"


class AdminForbidden(GatewayError):
    status_code = 401
    error_type = "authentication_error"
    message = "Invalid or missing admin token"


class AccountForbidden(GatewayError):
    status_code = 403
    error_type = "permission_error"
    message = "This API key may not target that account"


class AccountNotFound(GatewayError):
    status_code = 404
    error_type = "not_found_error"
    message = "Account not found"


class CookieParseError(GatewayError):
    status_code = 400
    error_type = "invalid_request_error"
    message = "Could not parse cookies"


class CookieDecryptError(GatewayError):
    status_code = 500
    error_type = "api_error"
    message = "Could not decrypt stored cookies"


class KeyTargetRequired(GatewayError):
    status_code = 400
    error_type = "invalid_request_error"
    message = "generate requires either 'account_id' or 'cookies'"
