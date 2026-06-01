"""Inline BaseMethod for endpoints not yet wired into ClaudeAIClient (used by live tests)."""

from typing import Any

from claude_ai.methods.base import BaseMethod


class ListOrganizations(BaseMethod[None, list]):
    __endpoint__ = "/api/organizations"
    __http_method__ = "GET"
    __model__ = list

    def build_params(self, params: None) -> dict[str, Any]:
        del params
        return {"path": {}, "query": {}, "body": None, "headers": {}}

    def parse_response(self, data: Any) -> list:
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            return data["data"]
        return []
