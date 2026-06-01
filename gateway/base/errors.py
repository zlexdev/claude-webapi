"""GatewayError: root of the gateway exception tree.

Every gateway-domain error carries an HTTP status, an OpenAI-style error `type`,
and an optional stable `code`. The boundary error mapper (``shared/errors.py``)
turns any ``GatewayError`` into an OpenAI error envelope + status without needing
to know the concrete subclass. Raisers supply facts (args / context message);
the mapper owns presentation.
"""

from __future__ import annotations


class GatewayError(Exception):
    """Base for all gateway errors.

    Subclasses override the class attributes; raise sites may pass a context
    message and/or a stable ``code``. The default ``message`` is used when none
    is given at the raise site.
    """

    status_code: int = 500
    error_type: str = "internal_error"
    message: str = "Internal gateway error"

    def __init__(self, message: str | None = None, *, code: str | None = None) -> None:
        if message is not None:
            self.message = message
        self.code = code
        super().__init__(self.message)
