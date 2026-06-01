"""Default model-alias table + the set of real claude model ids.

Clients send arbitrary model strings (incl. joke names). Aliases here map them to a
claude model; real claude ids pass through; anything else falls back to the configured
default. Settings can extend/override via ``CLAUDE_GATEWAY_MODEL_ALIASES`` (D9).
"""

from __future__ import annotations

from claude_ai.enums.model import ClaudeModel

KNOWN_CLAUDE: frozenset[str] = frozenset(m.value for m in ClaudeModel)

DEFAULT_ALIASES: dict[str, str] = {
    "gemini-3.5-flash": ClaudeModel.HAIKU_4_5.value,
    "gemini-3.5-flash-thinking": ClaudeModel.SONNET_4_6.value,
    "gemini-3.5-pro": ClaudeModel.OPUS_4_6.value,
    "gpt-4o": ClaudeModel.SONNET_4_6.value,
    "gpt-4o-mini": ClaudeModel.HAIKU_4_5.value,
    "gpt-4-turbo": ClaudeModel.OPUS_4_6.value,
    "claude-3-opus": ClaudeModel.OPUS_4_6.value,
    "claude-3-sonnet": ClaudeModel.SONNET_4_6.value,
    "claude-3-haiku": ClaudeModel.HAIKU_4_5.value,
}
