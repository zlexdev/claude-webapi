"""DeleteMany: bulk-delete conversations by uuid list."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod


@dataclass(slots=True)
class DeleteManyParams:
    org_uuid: str
    conversation_uuids: list[str]

    def __post_init__(self) -> None:
        if not self.conversation_uuids:
            raise ValueError("conversation_uuids must not be empty")


class DeleteMany(BaseMethod[DeleteManyParams, None]):
    __endpoint__ = "/api/organizations/{org_uuid}/chat_conversations/delete_many"
    __http_method__ = "POST"
    __model__ = type(None)

    def build_params(self, params: DeleteManyParams) -> dict[str, Any]:
        return {
            "path": {"org_uuid": params.org_uuid},
            "body": {"conversation_uuids": params.conversation_uuids},
        }

    def parse_response(self, data: Any) -> None:
        return None
