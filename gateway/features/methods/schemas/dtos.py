"""DTOs for generic method dispatch + auto-docs."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class MethodStyle(StrEnum):
    FIELD = "field"  # RequestMethod (pydantic fields are the params)
    LEGACY = "legacy"  # BaseMethod + a <Name>Params dataclass


class MethodSpec(BaseModel):
    name: str
    group: str
    http_method: str
    endpoint: str
    style: MethodStyle
    is_stream: bool = False
    is_multipart: bool = False
    param_schema: dict[str, Any] = Field(default_factory=dict)
    result_model: str | None = None


class MethodInvokeRequest(BaseModel):
    method: str
    account_id: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    stream: bool = False


class MethodInvokeResult(BaseModel):
    method: str
    account_id: str
    result: Any = None


class MethodList(BaseModel):
    object: Literal["list"] = "list"
    data: list[MethodSpec]
