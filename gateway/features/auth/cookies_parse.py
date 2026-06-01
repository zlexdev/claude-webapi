"""parse_cookies: normalize a cookie input into ``dict[str, str]``.

Accepts three shapes used by browser exporters and the SDK:
- a flat ``{name: value}`` dict,
- a browser-export list of ``{"name": ..., "value": ...}`` objects,
- a string holding either of the above as JSON, or a Netscape ``cookies.txt`` dump.

The resulting dict is what ``HttpSession(cookies=...)`` expects (R-19).
"""

from __future__ import annotations

import json
from typing import Any

from gateway.features.auth.errors import CookieParseError

CookiesInput = dict[str, str] | list[dict[str, Any]] | str


def parse_cookies(value: CookiesInput) -> dict[str, str]:
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items()}
    if isinstance(value, list):
        return _from_list(value)
    if isinstance(value, str):
        text = value.strip()
        if text[:1] in ("{", "["):
            try:
                return parse_cookies(json.loads(text))
            except json.JSONDecodeError as exc:
                raise CookieParseError(f"invalid cookie JSON: {exc}") from exc
        return _from_netscape(text)
    raise CookieParseError("unsupported cookie input type")


def _from_list(items: list[dict[str, Any]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in items:
        name = item.get("name")
        if name is None or "value" not in item:
            continue
        out[str(name)] = str(item["value"])
    if not out:
        raise CookieParseError("cookie list contained no {name, value} entries")
    return out


def _from_netscape(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) >= 7:  # domain, flag, path, secure, expiry, name, value
            out[fields[5]] = fields[6]
    if not out:
        raise CookieParseError("no cookies found in Netscape input")
    return out
