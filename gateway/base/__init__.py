"""Gateway base contracts: abstract, zero business logic."""

from gateway.base.errors import GatewayError
from gateway.base.service import BaseService

__all__ = ["BaseService", "GatewayError"]
