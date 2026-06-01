"""Project, ProjectDoc, ProjectFile, KBStats models."""

from typing import Any

from claude_ai.models._object import ClaudeObject


class ProjectPermissions(ClaudeObject):
    can_edit: bool = False
    can_delete: bool = False
    can_manage_members: bool = False


class ProjectDoc(ClaudeObject):
    uuid: str
    file_name: str = ""
    content: str | None = None
    created_at: str | None = None


class ProjectFile(ClaudeObject):
    uuid: str
    file_name: str = ""
    content: str | None = None
    created_at: str | None = None


class ProjectSync(ClaudeObject):
    uuid: str | None = None
    provider: str | None = None
    status: str | None = None
    synced_at: str | None = None


class KBStats(ClaudeObject):
    total_docs: int = 0
    total_tokens: int = 0


class Project(ClaudeObject):
    uuid: str
    name: str = ""
    description: str = ""
    is_private: bool = True
    creator: dict[str, Any] | None = None
    is_starred: bool = False
    is_starter_project: bool = False
    is_harmony_project: bool = False
    type: str | None = None
    subtype: str | None = None
    settings: dict[str, Any] | None = None
    archived_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    permissions: list[Any] = []
    docs_count: int | None = None
