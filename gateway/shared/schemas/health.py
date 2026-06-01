"""HealthResponse — the shape returned by the unauthenticated ``GET /health`` probe."""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    server: str
