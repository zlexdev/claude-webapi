"""Unit tests for cookie/XSRF helpers."""

from claude_ai.session.auth import (
    build_auth_headers,
    cookies_from_set_cookie,
    extract_xsrf,
    parse_set_cookie,
)


class TestExtractXsrf:
    def test_uppercase_name(self) -> None:
        assert extract_xsrf({"XSRF-TOKEN": "abc"}) == "abc"

    def test_lowercase_fallback(self) -> None:
        assert extract_xsrf({"xsrf_token": "xyz"}) == "xyz"

    def test_url_decoded(self) -> None:
        assert extract_xsrf({"XSRF-TOKEN": "a%2Fb%3Dc"}) == "a/b=c"

    def test_missing(self) -> None:
        assert extract_xsrf({"sessionKey": "sk"}) is None

    def test_uppercase_wins_over_lowercase(self) -> None:
        result = extract_xsrf({"XSRF-TOKEN": "upper", "xsrf_token": "lower"})
        assert result == "upper"


class TestBuildAuthHeaders:
    def test_serializes_cookies(self) -> None:
        headers = build_auth_headers({"sessionKey": "sk", "XSRF-TOKEN": "x"})
        assert "cookie" in headers
        assert "sessionKey=sk" in headers["cookie"]
        assert "XSRF-TOKEN=x" in headers["cookie"]

    def test_includes_xsrf_header_when_present(self) -> None:
        headers = build_auth_headers({"XSRF-TOKEN": "tok"})
        assert headers["x-xsrf-token"] == "tok"

    def test_no_xsrf_header_when_absent(self) -> None:
        headers = build_auth_headers({"sessionKey": "sk"})
        assert "x-xsrf-token" not in headers

    def test_empty_cookies_yields_empty_dict(self) -> None:
        assert build_auth_headers({}) == {}


class TestParseSetCookie:
    def test_simple(self) -> None:
        assert parse_set_cookie("foo=bar; Path=/; Secure") == ("foo", "bar")

    def test_no_equals_returns_none(self) -> None:
        assert parse_set_cookie("just-a-flag") is None

    def test_empty_value_allowed(self) -> None:
        assert parse_set_cookie("foo=; Path=/") == ("foo", "")

    def test_invalid_name_rejected(self) -> None:
        assert parse_set_cookie("foo bar=v") is None

    def test_control_chars_in_value_rejected(self) -> None:
        assert parse_set_cookie("foo=ba\x00r") is None


class TestCookiesFromSetCookie:
    def test_picks_only_set_cookie_headers(self) -> None:
        headers = {
            "Set-Cookie": "a=1; Path=/",
            "Content-Type": "text/html",
        }
        assert cookies_from_set_cookie(headers) == {"a": "1"}

    def test_case_insensitive_header_name(self) -> None:
        headers = {"set-cookie": "a=1"}
        assert cookies_from_set_cookie(headers) == {"a": "1"}

    def test_empty_when_no_cookies(self) -> None:
        assert cookies_from_set_cookie({"Content-Type": "text/html"}) == {}
