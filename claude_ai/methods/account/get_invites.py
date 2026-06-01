"""GetInvites: pending organization invites for an account."""

from typing import Any

from claude_ai.methods.base import RequestMethod


class GetInvites(RequestMethod[list[Any]]):
    __endpoint__ = "/api/accounts/{account_uuid}/invites"
    __http_method__ = "GET"
    __model__ = list

    account_uuid: str

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {"path": {"account_uuid": self.account_uuid}}

    def parse_response(self, data: Any) -> list[Any]:
        return data if isinstance(data, list) else []
