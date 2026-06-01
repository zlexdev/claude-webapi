"""resolve_client: map an account_id to its live orchestrator client, or 404.

Shared by the completion / chats / methods features so none of them import another
feature (backend law #3) just to turn an ``account_id`` into a client.
"""

from __future__ import annotations

from typing import Any

from gateway.base.errors import GatewayError


class AccountUnavailable(GatewayError):
    status_code = 404
    error_type = "not_found_error"
    message = "Account is not registered in the pool"


async def resolve_client(orchestrator: Any, account_id: str) -> Any:
    try:
        return await orchestrator.get(account_id)
    except KeyError:
        raise AccountUnavailable(f"account {account_id!r} is not registered") from None
