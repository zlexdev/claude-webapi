"""BaseMethod and MethodRequest: envelope-based endpoint contract. build_params() returns {path,query,body,headers}."""

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

P = TypeVar("P")
R = TypeVar("R")


class MethodRequest:
    __slots__ = ("url", "query", "body", "headers")

    def __init__(
        self,
        url: str,
        query: dict[str, Any],
        body: dict[str, Any] | None,
        headers: dict[str, str],
    ) -> None:
        self.url = url
        self.query = query
        self.body = body
        self.headers = headers


class BaseMethod(ABC, Generic[P, R]):
    __endpoint__: ClassVar[str]
    __http_method__: ClassVar[str] = "GET"
    __model__: ClassVar[type[Any]]
    __is_stream__: ClassVar[bool] = False
    __is_multipart__: ClassVar[bool] = False

    @abstractmethod
    def build_params(self, params: P) -> dict[str, Any]: ...

    def build_request(self, base_url: str, params: P) -> MethodRequest:
        raw = self.build_params(params)
        path_params = raw.get("path", {})
        url = f"{base_url}{self.__endpoint__}"
        for key, value in path_params.items():
            url = url.replace(f"{{{key}}}", str(value))
        return MethodRequest(
            url=url,
            query=raw.get("query", {}),
            body=raw.get("body"),
            headers=raw.get("headers", {}),
        )

    def parse_response(self, data: Any) -> R:
        model = self.__model__
        if (
            isinstance(data, dict)
            and isinstance(model, type)
            and issubclass(model, BaseModel)
        ):
            return model.model_validate(data)  # type: ignore[return-value]
        return data  # type: ignore[return-value]


class RequestMethod(BaseModel, BaseMethod[None, R], Generic[R]):
    """BaseMethod whose request parameters are Pydantic fields, not a Params DTO.

    Generic over the response type `R` (mirrors `BaseMethod[P, R]`): subclasses
    declare `RequestMethod[LoginMethods]` so `parse_response` is typed. Used by
    HAR-derived methods: instantiate `Method(field=...)` directly, the field
    values are read by `build_params(self)`. The legacy `BaseMethod` +
    `@dataclass Params` style is kept for the original endpoints (not migrated).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def build_params(self, params: Any = None) -> dict[str, Any]:
        return {}
