"""GetCredits: remaining credits for an organization."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod
from claude_ai.models.organization import Credits


@dataclass(slots=True)
class GetCreditsParams:
    org_uuid: str


class GetCredits(BaseMethod[GetCreditsParams, Credits]):
    __endpoint__ = "/api/organizations/{org_uuid}/prepaid/credits"
    __http_method__ = "GET"
    __model__ = Credits

    def build_params(self, params: GetCreditsParams) -> dict[str, Any]:
        return {
            "path": {"org_uuid": params.org_uuid},
        }
