"""UserAgent middleware: injects a browser-like UA + standard navigator headers into every TransportRequest."""

import uuid as _uuid
from typing import Any

from claude_ai.middleware.base import Middleware, NextHandler
from claude_ai.transport.base import TransportRequest, TransportResponse

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/146.0.0.0 Safari/537.36"
)


def _base_headers(device_id: str) -> dict[str, str]:
    return {
        "user-agent": _UA,
        "accept-language": "en-US,en;q=0.9",
        # br/zstd needs `brotli`/`zstandard` lib for httpx to decode — skip.
        "origin": "https://claude.ai",
        "referer": "https://claude.ai/",
        "priority": "u=1, i",
        "sec-ch-ua": '"Chromium";v="146", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sec-gpc": "1",
        "anthropic-client-platform": "web_claude_ai",
        "anthropic-device-id": device_id,
    }


class BrowserHeadersMiddleware(Middleware[TransportRequest, TransportResponse]):
    def __init__(self, *, device_id: str | None = None) -> None:
        self._headers = _base_headers(device_id or str(_uuid.uuid4()))

    async def __call__(
        self,
        handler: NextHandler[TransportRequest, TransportResponse],
        event: TransportRequest,
        data: dict[str, Any],
    ) -> TransportResponse:
        for k, v in self._headers.items():
            event.headers.setdefault(k, v)
        if "accept" not in event.headers:
            event.headers["accept"] = "*/*"
        return await handler(event, data)
