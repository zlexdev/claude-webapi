"""AcceptLegalDocs: acknowledge consumer-terms / privacy / AUP document versions.

Each acceptance is ``{"document_id": "v3:<kind>:<uuid>", "accepted_via_checkbox": bool}``.
"""

from typing import Any

from claude_ai.methods.base import RequestMethod


class AcceptLegalDocs(RequestMethod[None]):
    __endpoint__ = "/api/account/accept_legal_docs"
    __http_method__ = "PUT"
    __model__ = type(None)

    acceptances: list[dict[str, Any]]

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {"body": {"acceptances": self.acceptances}}
