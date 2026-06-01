"""BaseService: marker ABC for service identity + DI discovery (no behavior)."""

from __future__ import annotations

from abc import ABC


class BaseService(ABC):
    """Root of every gateway service.

    Intentionally empty: its job is type identity and dependency-injection
    discovery, not shared behavior. Services hold all business logic and never
    import a web framework.
    """
