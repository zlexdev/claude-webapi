"""GetAccess: feature flags and access info for an organization."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod
from claude_ai.models.account import AccessInfo


@dataclass(slots=True)
class GetAccessParams:
    org_uuid: str


class GetAccess(BaseMethod[GetAccessParams, AccessInfo]):
    __endpoint__ = "/api/organizations/{org_uuid}/my-access"
    __http_method__ = "GET"
    __model__ = AccessInfo

    def build_params(self, params: GetAccessParams) -> dict[str, Any]:
        return {
            "path": {"org_uuid": params.org_uuid},
        }
