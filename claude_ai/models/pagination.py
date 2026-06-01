"""Generic PaginatedResponse[T] wrapper."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T] = []
    has_more: bool = False
    cursor: str | None = None
