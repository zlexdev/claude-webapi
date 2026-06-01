"""UploadFile: multipart upload of an attachment to a conversation."""

import mimetypes
from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod
from claude_ai.models.artifact import WiggleUploadResult


@dataclass(slots=True)
class UploadFileParams:
    org_uuid: str
    conv_uuid: str
    file_content: bytes
    file_name: str

    def __post_init__(self) -> None:
        if not self.file_content:
            raise ValueError("file_content must not be empty")
        if not self.file_name:
            raise ValueError("file_name must not be empty")


class UploadFile(BaseMethod[UploadFileParams, WiggleUploadResult]):
    __endpoint__ = (
        "/api/organizations/{org_uuid}/conversations/{conv_uuid}/wiggle/upload-file"
    )
    __http_method__ = "POST"
    __model__ = WiggleUploadResult
    __is_multipart__ = True

    def build_params(self, params: UploadFileParams) -> dict[str, Any]:
        return {
            "path": {"org_uuid": params.org_uuid, "conv_uuid": params.conv_uuid},
        }

    def build_multipart(
        self, params: UploadFileParams
    ) -> dict[str, tuple[str, bytes, str]]:
        mime = mimetypes.guess_type(params.file_name)[0] or "application/octet-stream"
        return {"file": (params.file_name, params.file_content, mime)}
