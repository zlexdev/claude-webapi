"""GetMemorySettings: per-org memory (Saffron / Melange) enablement + mode."""

from typing import Any

from claude_ai.methods.base import RequestMethod
from claude_ai.models.settings import MemorySettings


class GetMemorySettings(RequestMethod[MemorySettings]):
    __endpoint__ = "/api/organizations/{org_uuid}/memory/settings"
    __http_method__ = "GET"
    __model__ = MemorySettings

    org_uuid: str

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {"path": {"org_uuid": self.org_uuid}}
