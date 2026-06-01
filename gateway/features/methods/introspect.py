"""Introspect SDK method classes into MethodSpec + locate their param shape.

Two coexisting styles:
- field-based ``RequestMethod`` (a pydantic ``BaseModel``) — params are the model's fields;
- legacy ``BaseMethod`` + a sibling ``<Name>Params`` dataclass.

Discovery walks the ``claude_ai.methods`` subpackages' ``__all__`` exports, so new SDK
methods appear in dispatch + docs with zero gateway changes.
"""

from __future__ import annotations

import dataclasses
import importlib
import pkgutil
from typing import Any

from pydantic import BaseModel

import claude_ai.methods as methods_pkg
from claude_ai.methods.base import BaseMethod, RequestMethod
from gateway.features.methods.schemas.dtos import MethodSpec, MethodStyle

Entry = tuple[MethodSpec, type[Any], type[Any] | None]


def _type_name(annotation: Any) -> str:
    return getattr(annotation, "__name__", None) or str(annotation)


def _result_model_name(cls: type[Any]) -> str | None:
    model = getattr(cls, "__model__", None)
    return model.__name__ if isinstance(model, type) else None


def _legacy_schema(params_cls: type[Any] | None) -> dict[str, Any]:
    if params_cls is None or not dataclasses.is_dataclass(params_cls):
        return {"type": "object", "properties": {}}
    properties: dict[str, Any] = {}
    required: list[str] = []
    for field in dataclasses.fields(params_cls):
        properties[field.name] = {"type": _type_name(field.type)}
        if field.default is dataclasses.MISSING and field.default_factory is dataclasses.MISSING:
            required.append(field.name)
    return {"type": "object", "properties": properties, "required": required}


def _param_schema(cls: type[Any], style: MethodStyle, params_cls: type[Any] | None) -> dict[str, Any]:
    if style is MethodStyle.FIELD:
        return cls.model_json_schema()  # type: ignore[no-any-return]  # cls is BaseModel here
    return _legacy_schema(params_cls)


def extract_spec(cls: type[Any], group: str, params_cls: type[Any] | None) -> MethodSpec:
    style = MethodStyle.FIELD if issubclass(cls, BaseModel) else MethodStyle.LEGACY
    return MethodSpec(
        name=cls.__name__,
        group=group,
        http_method=getattr(cls, "__http_method__", "GET"),
        endpoint=getattr(cls, "__endpoint__", ""),
        style=style,
        is_stream=bool(getattr(cls, "__is_stream__", False)),
        is_multipart=bool(getattr(cls, "__is_multipart__", False)),
        param_schema=_param_schema(cls, style, params_cls),
        result_model=_result_model_name(cls),
    )


def discover() -> dict[str, Entry]:
    entries: dict[str, Entry] = {}
    for module_info in pkgutil.iter_modules(methods_pkg.__path__):
        if not module_info.ispkg:
            continue
        group = module_info.name
        module = importlib.import_module(f"claude_ai.methods.{group}")
        for attr in getattr(module, "__all__", []):
            obj = getattr(module, attr, None)
            if not (isinstance(obj, type) and issubclass(obj, BaseMethod)):
                continue
            if obj in (BaseMethod, RequestMethod):
                continue
            params_cls = getattr(module, f"{attr}Params", None)
            entries[obj.__name__] = (extract_spec(obj, group, params_cls), obj, params_cls)
    return entries


def legacy_has_field(params_cls: type[Any] | None, name: str) -> bool:
    if params_cls is None or not dataclasses.is_dataclass(params_cls):
        return False
    return any(f.name == name for f in dataclasses.fields(params_cls))
