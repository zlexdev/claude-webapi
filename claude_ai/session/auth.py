"""Pure cookie/XSRF helpers: extract_xsrf, build_auth_headers, parse_set_cookie."""

from __future__ import annotations

import re
from urllib.parse import unquote

_COOKIE_NAME_RE = re.compile(r"^[\w\-\.]+$")
_COOKIE_UNSAFE_RE = re.compile(r"[\x00-\x1f\x7f]")
_XSRF_NAMES = ("XSRF-TOKEN", "xsrf_token")


def extract_xsrf(cookies: dict[str, str]) -> str | None:
    for name in _XSRF_NAMES:
        if name in cookies:
            return unquote(cookies[name])
    return None


def build_auth_headers(cookies: dict[str, str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    if cookies:
        headers["cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
    xsrf = extract_xsrf(cookies)
    if xsrf:
        headers["x-xsrf-token"] = xsrf
    return headers


def parse_set_cookie(header: str) -> tuple[str, str] | None:
    pair = header.strip().split(";")[0]
    if "=" not in pair:
        return None
    name, _, value = pair.partition("=")
    name = name.strip()
    value = value.strip()
    if not _COOKIE_NAME_RE.match(name) or _COOKIE_UNSAFE_RE.search(value):
        return None
    return name, value


def cookies_from_set_cookie(headers: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in headers.items():
        if k.lower() != "set-cookie":
            continue
        parsed = parse_set_cookie(v)
        if parsed is not None:
            out[parsed[0]] = parsed[1]
    return out
