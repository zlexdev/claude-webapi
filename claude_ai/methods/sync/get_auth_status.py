"""GetSyncAuthStatus: per-provider auth status."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod
from claude_ai.models.sync import SyncAuth


@dataclass(slots=True)
class GetSyncAuthStatusParams:
    org_uuid: str
    provider: str


class GetSyncAuthStatus(BaseMethod[GetSyncAuthStatusParams, SyncAuth]):
    __endpoint__ = "/api/organizations/{org_uuid}/sync/{provider}/auth"
    __http_method__ = "GET"
    __model__ = SyncAuth

    def build_params(self, params: GetSyncAuthStatusParams) -> dict[str, Any]:
        return {
            "path": {"org_uuid": params.org_uuid, "provider": params.provider},
        }
