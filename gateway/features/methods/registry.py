"""MethodRegistry: discover SDK methods once, then look up + build instances for dispatch."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from gateway.features.methods.errors import (
    MethodParamsInvalid,
    MultipartNotSupported,
    UnknownMethod,
)
from gateway.features.methods.introspect import Entry, discover, legacy_has_field
from gateway.features.methods.schemas.dtos import MethodSpec, MethodStyle


class MethodRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, Entry] = discover()

    def get(self, name: str) -> MethodSpec:
        entry = self._entries.get(name)
        if entry is None:
            raise UnknownMethod(f"unknown method {name!r}")
        return entry[0]

    def all_specs(self) -> list[MethodSpec]:
        return sorted(
            (e[0] for e in self._entries.values()), key=lambda s: (s.group, s.name)
        )

    def build_instance(
        self, name: str, params: dict[str, Any], *, org_uuid: str | None = None
    ) -> tuple[Any, Any | None]:
        """Return ``(method, params_or_None)`` ready for ``await client(method[, params])``.

        Injects ``org_uuid`` from the account's client when the method declares it and the
        caller omitted it. Raises 400 for multipart, 422 for bad params.
        """
        entry = self._entries.get(name)
        if entry is None:
            raise UnknownMethod(f"unknown method {name!r}")
        spec, method_cls, params_cls = entry
        if spec.is_multipart:
            raise MultipartNotSupported(f"{name} is multipart")

        supplied = dict(params)
        if spec.style is MethodStyle.FIELD:
            if org_uuid and "org_uuid" in method_cls.model_fields and "org_uuid" not in supplied:
                supplied["org_uuid"] = org_uuid
            try:
                return method_cls(**supplied), None
            except (ValidationError, TypeError) as exc:
                raise MethodParamsInvalid(f"{name}: {exc}") from exc

        if params_cls is None:
            raise MethodParamsInvalid(f"{name} has no Params class")
        if org_uuid and legacy_has_field(params_cls, "org_uuid") and "org_uuid" not in supplied:
            supplied["org_uuid"] = org_uuid
        try:
            return method_cls(), params_cls(**supplied)
        except (TypeError, ValueError) as exc:
            raise MethodParamsInvalid(f"{name}: {exc}") from exc
