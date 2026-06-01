"""GetStyles: personalized response styles for an org."""

from dataclasses import dataclass
from typing import Any

from pydantic import TypeAdapter

from claude_ai.methods.base import BaseMethod
from claude_ai.models.organization import Style

_style_list_adapter = TypeAdapter(list[Style])


@dataclass(slots=True)
class GetStylesParams:
    org_uuid: str


class GetStyles(BaseMethod[GetStylesParams, list[Style]]):
    __endpoint__ = "/api/organizations/{org_uuid}/list_styles"
    __http_method__ = "GET"
    __model__ = list

    def build_params(self, params: GetStylesParams) -> dict[str, Any]:
        return {
            "path": {"org_uuid": params.org_uuid},
        }

    def parse_response(self, data: Any) -> list[Style]:
        if isinstance(data, dict):
            collected: list[Any] = []
            for key in ("defaultStyles", "customStyles"):
                value = data.get(key)
                if isinstance(value, list):
                    collected.extend(value)
            data = collected
        return _style_list_adapter.validate_python(data)
