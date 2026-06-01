"""Sync provider models (Drive, ingestion progress, auth status)."""

from claude_ai.models._object import ClaudeObject


class SyncAuth(ClaudeObject):
    authenticated: bool = False
    provider: str | None = None
    account: str | None = None


class SyncSettings(ClaudeObject):
    enabled_providers: list[str] = []


class DriveRecent(ClaudeObject):
    id: str = ""
    name: str = ""
    mime_type: str | None = None
    modified_time: str | None = None


class IngestionProgress(ClaudeObject):
    status: str | None = None
    progress: float = 0.0
    total_files: int = 0
    processed_files: int = 0
