"""Stdlib logging for the gateway: structured via ``extra=``, request_id-bound.

Matches the repo convention (``logging.getLogger``, no ``print``). A ``request_id``
is carried in a ``contextvars.ContextVar`` so every log line under one request
inherits it without threading it through call sites. The per-framework server
adapters call :func:`bind_request_id` at request entry.
"""

from __future__ import annotations

import contextvars
import logging

_LOGGER_ROOT = "claude_gateway"

_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "gateway_request_id", default=None
)


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id.get() or "-"
        return True


def configure_logging(level: int = logging.INFO) -> None:
    """Install a single handler on the ``claude_gateway`` logger. Idempotent."""
    handler = logging.StreamHandler()
    handler.addFilter(_RequestIdFilter())
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"
        )
    )
    root = logging.getLogger(_LOGGER_ROOT)
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a logger under the ``claude_gateway`` namespace."""
    if not name or name == _LOGGER_ROOT:
        return logging.getLogger(_LOGGER_ROOT)
    return logging.getLogger(f"{_LOGGER_ROOT}.{name}")


def bind_request_id(request_id: str) -> contextvars.Token[str | None]:
    """Bind a request id for the current context; returns a token to reset with."""
    return _request_id.set(request_id)


def reset_request_id(token: contextvars.Token[str | None]) -> None:
    _request_id.reset(token)


def current_request_id() -> str | None:
    return _request_id.get()
