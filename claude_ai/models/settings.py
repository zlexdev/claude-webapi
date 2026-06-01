"""Org-scoped settings and catalogue models (cowork, memory, skills, marketplaces)."""

from typing import Any

from claude_ai.models._object import ClaudeObject


class CoworkSettings(ClaudeObject):
    enabled: bool | None = None
    can_be_enabled: bool | None = None
    dittos_enabled: bool | None = None
    first_enabled_at: str | None = None
    skip_approvals_enabled: bool | None = None


class MemorySettings(ClaudeObject):
    memory_mode: str | None = None
    enabled_melange: bool | None = None
    enabled_saffron: bool | None = None
    enabled_saffron_search: bool | None = None


class DiscoverableOrgs(ClaudeObject):
    can_create_personal: bool = False
    organizations: list[dict[str, Any]] = []


class Skill(ClaudeObject):
    id: str
    name: str
    description: str | None = None
    enabled: bool | None = None
    source: str | None = None
    creator_type: str | None = None
    is_shared: bool | None = None
    is_public_provisioned: bool | None = None
    enable_count: int | None = None
    updated_at: str | None = None


class SkillList(ClaudeObject):
    skills: list[Skill] = []


class Marketplace(ClaudeObject):
    id: str
    name: str
    display_name: str | None = None
    description: str | None = None
    is_default: bool | None = None
    is_visible_for_org: bool | None = None
    source: str | None = None
    source_url: str | None = None
    auto_sync_on_push: bool | None = None
    created_at: str | None = None


class MarketplaceList(ClaudeObject):
    marketplaces: list[Marketplace] = []


class UserSettingsWriteResult(ClaudeObject):
    checksum: str | None = None
    lastModified: str | None = None
