"""SQLAlchemy 2.0 (async) data layer.

Kept import-light: this package's submodules import SQLAlchemy, so they are imported
*only* by the Postgres store backend (loaded lazily when ``CLAUDE_GATEWAY_DB=postgres``).
The Memory backend and the rest of the gateway never import SQLAlchemy.

Public pieces (import from the submodules directly):
- ``gateway.shared.db.orm``    — ``BaseOrm`` (DeclarativeBase) + ``TimestampMixin``
- ``gateway.shared.db.engine`` — ``Database`` (async engine + sessionmaker + create_all)
- ``gateway.shared.db.repo``   — ``BaseRepo[TRow]`` generic CRUD + keyset cursor pagination
"""
