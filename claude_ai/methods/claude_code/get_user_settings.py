"""GetClaudeCodeSettings: per-user Claude Code settings store (KV blob)."""

from typing import Any

from claude_ai.methods.base import RequestMethod


class GetClaudeCodeSettings(RequestMethod[dict[str, Any]]):
    __endpoint__ = "/api/claude_code/organizations/{org_uuid}/user_settings"
    __http_method__ = "GET"
    __model__ = dict

    org_uuid: str

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {"path": {"org_uuid": self.org_uuid}}
