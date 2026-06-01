"""GetSyncSettings: enabled providers and settings."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod
from claude_ai.models.sync import SyncSettings


@dataclass(slots=True)
class GetSyncSettingsParams:
    org_uuid: str


class GetSyncSettings(BaseMethod[GetSyncSettingsParams, SyncSettings]):
    __endpoint__ = "/api/organizations/{org_uuid}/sync/settings"
    __http_method__ = "GET"
    __model__ = SyncSettings

    def build_params(self, params: GetSyncSettingsParams) -> dict[str, Any]:
        return {
            "path": {"org_uuid": params.org_uuid},
        }
