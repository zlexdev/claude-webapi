"""GetOrganization: organization profile."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod
from claude_ai.models.organization import Organization


@dataclass(slots=True)
class GetOrganizationParams:
    org_uuid: str


class GetOrganization(BaseMethod[GetOrganizationParams, Organization]):
    __endpoint__ = "/api/organizations/{org_uuid}"
    __http_method__ = "GET"
    __model__ = Organization

    def build_params(self, params: GetOrganizationParams) -> dict[str, Any]:
        return {
            "path": {"org_uuid": params.org_uuid},
        }
