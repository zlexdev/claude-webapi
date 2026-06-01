"""GatewaySettings: env-loaded gateway configuration (CLAUDE_GATEWAY_ prefix)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CLAUDE_GATEWAY_", env_file=".env", extra="ignore"
    )

    server: Literal["fastapi", "litestar", "aiohttp"] = "fastapi"
    host: str = "0.0.0.0"
    port: int = 8081

    db: Literal["postgres", "memory"] = "postgres"
    database_url: str | None = None

    # Required control-surface secret — instantiation fails if unset (D12).
    admin_token: str

    default_model: str = "claude-sonnet-4-6"
    # Merged over DEFAULT_ALIASES by ModelMapper; env accepts a JSON object.
    model_aliases: dict[str, str] = Field(default_factory=dict)

    rate_limit_per_min: int = 120
    cookie_encryption_key: str | None = None

    @model_validator(mode="after")
    def _require_database_url_for_postgres(self) -> GatewaySettings:
        if self.db == "postgres" and not self.database_url:
            raise ValueError(
                "CLAUDE_GATEWAY_DATABASE_URL is required when CLAUDE_GATEWAY_DB=postgres"
            )
        return self
