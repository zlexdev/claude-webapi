"""ClaudeAISettings: env-loaded configuration (CLAUDE_AI_ prefix)."""

from typing import Literal

from pydantic_settings import BaseSettings

from claude_ai.enums.model import ClaudeModel


class ClaudeAISettings(BaseSettings):
    model_config = {"env_prefix": "CLAUDE_AI_"}

    base_url: str = "https://claude.ai"
    # HTTP transport backend. aiohttp is the default; httpx remains available.
    transport: Literal["aiohttp", "httpx"] = "aiohttp"
    # Sent on every request. Cloudflare binds the cf_clearance cookie to the exact
    # UA that earned it — set this to match the browser the cookies were harvested
    # from, or CF re-challenges (default: Chrome 148 on Win64).
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
    )
    default_model: ClaudeModel = ClaudeModel.SONNET_4_6
    timeout: float = 120.0
    stream_timeout: float = 600.0
    max_retries: int = 3
    retry_backoff: float = 1.0
    locale: str = "en-US"
    timezone: str = "UTC"
    rendering_mode: str = "messages"
