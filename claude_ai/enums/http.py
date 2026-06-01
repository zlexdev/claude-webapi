"""HTTP-layer enums: HttpMethod, EnvelopeKey, OrderBy, ProjectFilter, StyleType."""

from enum import StrEnum


class HttpMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class EnvelopeKey(StrEnum):
    PATH = "path"
    QUERY = "query"
    BODY = "body"
    HEADERS = "headers"


class OrderBy(StrEnum):
    UPDATED_AT = "updated_at"
    CREATED_AT = "created_at"
    NAME = "name"


class ProjectFilter(StrEnum):
    ALL = "all"
    ACTIVE = "active"
    ARCHIVED = "archived"


class StyleType(StrEnum):
    DEFAULT = "default"
    CUSTOM = "custom"
