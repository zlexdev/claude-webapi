"""DownloadFile: fetch raw bytes for a conversation artifact."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod


@dataclass(slots=True)
class DownloadFileParams:
    org_uuid: str
    conv_uuid: str
    path: str


class DownloadFile(BaseMethod[DownloadFileParams, bytes]):
    __endpoint__ = (
        "/api/organizations/{org_uuid}/conversations/{conv_uuid}/wiggle/download-file"
    )
    __http_method__ = "GET"
    __model__ = bytes

    def build_params(self, params: DownloadFileParams) -> dict[str, Any]:
        return {
            "path": {"org_uuid": params.org_uuid, "conv_uuid": params.conv_uuid},
            "query": {"path": params.path},
        }

    def parse_response(self, data: Any) -> bytes:
        if isinstance(data, bytes):
            return data
        if isinstance(data, str):
            return data.encode()
        return bytes(data)
