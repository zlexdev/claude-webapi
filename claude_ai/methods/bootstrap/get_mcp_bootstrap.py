"""GetMcpBootstrap: MCP connector bootstrap config for an org."""

from typing import Any

from claude_ai.methods.base import RequestMethod


class GetMcpBootstrap(RequestMethod[dict[str, Any]]):
    __endpoint__ = "/api/organizations/{org_uuid}/mcp/v2/bootstrap"
    __http_method__ = "GET"
    __model__ = dict

    org_uuid: str

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {"path": {"org_uuid": self.org_uuid}}
