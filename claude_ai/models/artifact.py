"""Artifact version and Wiggle upload-result models."""

from typing import Any

from claude_ai.models._object import ClaudeObject


class ArtifactVersion(ClaudeObject):
    uuid: str
    version: int = 0
    content: str | None = None
    created_at: str | None = None


class WiggleUploadResult(ClaudeObject):
    success: bool
    path: str
    sanitized_name: str
    file_kind: str = "blob"
    file_uuid: str = ""
    file_name: str = ""
    size_bytes: int = 0
    uuid: str = ""
    created_at: str | None = None


class WiggleFile(ClaudeObject):
    path: str
    name: str = ""
    size: int = 0


class WiggleStorageInfo(ClaudeObject):
    used: int = 0
    total: int = 0
    files: list[dict[str, Any]] = []
