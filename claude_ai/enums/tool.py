"""Tool type identifiers exposed by claude.ai."""

from enum import StrEnum


class ToolType(StrEnum):
    WEB_SEARCH = "web_search_v0"
    ARTIFACTS = "artifacts_v0"
    REPL = "repl_v0"
    WIDGET = "widget"
