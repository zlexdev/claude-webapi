"""Exception hierarchy: ClaudeAIError + APIError subclasses + NetworkError/StreamError/SessionError."""

from typing import Any


class ClaudeAIError(Exception):
    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        self.context = context or {}
        super().__init__(message)


class APIError(ClaudeAIError):
    def __init__(
        self,
        status_code: int,
        detail: str,
        *,
        request_url: str = "",
        request_method: str = "",
        error_code: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        self.request_url = request_url
        self.request_method = request_method
        self.error_code = error_code
        super().__init__(
            f"[{status_code}] {detail}",
            context={
                "status_code": status_code,
                "url": request_url,
                "method": request_method,
                "error_code": error_code,
            },
        )


class BadRequestError(APIError):
    pass


class AuthError(APIError):
    pass


class ForbiddenError(APIError):
    pass


class NotFoundError(APIError):
    pass


class RateLimitError(APIError):
    def __init__(
        self,
        status_code: int = 429,
        detail: str = "Rate limited",
        *,
        retry_after: float | None = None,
        request_url: str = "",
        request_method: str = "",
        error_code: str | None = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(
            status_code,
            detail,
            request_url=request_url,
            request_method=request_method,
            error_code=error_code,
        )


class ServerError(APIError):
    pass


class StreamError(ClaudeAIError):
    def __init__(self, event_type: str, raw_data: str, reason: str = "") -> None:
        self.event_type = event_type
        self.raw_data = raw_data
        super().__init__(
            f"Stream error on event '{event_type}': {reason}",
            context={"event_type": event_type, "raw_data": raw_data[:500]},
        )


class SessionError(ClaudeAIError):
    def __init__(self, reason: str, *, session_id: str = "") -> None:
        self.session_id = session_id
        super().__init__(reason, context={"session_id": session_id})


class NetworkError(ClaudeAIError):
    def __init__(self, url: str, original: Exception) -> None:
        self.url = url
        self.original = original
        super().__init__(f"Network error: {url}", context={"url": url})


STATUS_MAP: dict[int, type[APIError]] = {
    400: BadRequestError,
    401: AuthError,
    403: ForbiddenError,
    404: NotFoundError,
    429: RateLimitError,
    500: ServerError,
    502: ServerError,
    503: ServerError,
}


def raise_for_status(status_code: int, detail: str, **kwargs: Any) -> None:
    exc_cls = STATUS_MAP.get(status_code, APIError)
    raise exc_cls(status_code=status_code, detail=detail, **kwargs)
