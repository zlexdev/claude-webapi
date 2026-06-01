"""UpdateClaudeCodeSettings: write entries into the Claude Code user settings store.

`entries` maps a settings key (e.g. ``ccd/dframe-starred-cowork-remote``) to a
JSON-encoded string value; the server returns the new checksum + lastModified.
"""

from typing import Any

from claude_ai.methods.base import RequestMethod
from claude_ai.models.settings import UserSettingsWriteResult


class UpdateClaudeCodeSettings(RequestMethod[UserSettingsWriteResult]):
    __endpoint__ = "/api/claude_code/organizations/{org_uuid}/user_settings"
    __http_method__ = "PUT"
    __model__ = UserSettingsWriteResult

    org_uuid: str
    entries: dict[str, str]

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {
            "path": {"org_uuid": self.org_uuid},
            "body": {"entries": self.entries},
        }
