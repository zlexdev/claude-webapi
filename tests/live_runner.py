"""Live integration runner: drives the real claude.ai API with a sessionKey cookie.

Usage:
  python tests/live_runner.py [--session-key sk-ant-sid02-...]
or set CLAUDE_SESSION_KEY env var.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import traceback
import uuid as _uuid
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:
        pass

from claude_ai import ClaudeAIClient, HttpSession, MemoryCache  # noqa: E402
from claude_ai.config import ClaudeAISettings  # noqa: E402
from claude_ai.exceptions import ClaudeAIError  # noqa: E402
from tests._http2_transport import Http2HttpxTransport  # noqa: E402
from tests._inline_methods import ListOrganizations  # noqa: E402
from tests._ua_middleware import BrowserHeadersMiddleware  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("live_runner")


@dataclass
class StepResult:
    name: str
    ok: bool
    detail: str = ""
    duration_ms: float = 0.0


@dataclass
class Report:
    steps: list[StepResult] = field(default_factory=list)

    def add(self, name: str, ok: bool, detail: str, dt: float) -> None:
        self.steps.append(StepResult(name, ok, detail, dt))
        marker = "OK " if ok else "FAIL"
        log.info("[%s] %-32s  %.0fms  %s", marker, name, dt, detail)

    def summary(self) -> str:
        passed = sum(1 for s in self.steps if s.ok)
        total = len(self.steps)
        lines = [f"\n=== Summary: {passed}/{total} passed ==="]
        for s in self.steps:
            lines.append(
                f"  {'OK ' if s.ok else 'FAIL'}  {s.name:<32}  {s.duration_ms:>6.0f}ms  {s.detail}"
            )
        return "\n".join(lines)


async def _step(report: Report, name: str, coro: Any) -> Any:
    t0 = perf_counter()
    try:
        result = await coro
        dt = (perf_counter() - t0) * 1000
        detail = _short_repr(result)
        report.add(name, True, detail, dt)
        return result
    except Exception as exc:
        dt = (perf_counter() - t0) * 1000
        report.add(name, False, f"{type(exc).__name__}: {exc}", dt)
        log.debug("Traceback for %s:\n%s", name, traceback.format_exc())
        return None


def _short_repr(value: Any, limit: int = 200) -> str:
    if value is None:
        return "None"
    if isinstance(value, list):
        return f"list[{len(value)}]"
    if hasattr(value, "model_dump"):
        try:
            data = value.model_dump()
        except Exception:
            data = str(value)
        s = repr(data)
    else:
        s = repr(value)
    return s if len(s) <= limit else s[: limit - 1] + "…"


def parse_cookie_string(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for pair in raw.split(";"):
        pair = pair.strip()
        if not pair or "=" not in pair:
            continue
        name, _, value = pair.partition("=")
        name = name.strip()
        value = value.strip()
        if name:
            out[name] = value
    return out


def build_client(
    cookies: dict[str, str], *, transport_kind: str = "httpx"
) -> ClaudeAIClient:
    settings = ClaudeAISettings()
    transport: Any
    if transport_kind == "http2":
        transport = Http2HttpxTransport(
            base_url=settings.base_url, timeout=settings.timeout
        )
    elif transport_kind == "httpx":
        from claude_ai.transport.httpx import HttpxTransport

        transport = HttpxTransport(base_url=settings.base_url, timeout=settings.timeout)
    else:
        transport = None  # SDK default (aiohttp)
    device_id = cookies.get("anthropic-device-id")
    session = HttpSession(
        account_id="live-test",
        cookies=cookies,
        transport=transport,
        settings=settings,
    )
    session.use(BrowserHeadersMiddleware(device_id=device_id))
    return ClaudeAIClient(account_id="live-test", session=session, cache=MemoryCache())


async def run(cookies: dict[str, str], *, transport_kind: str = "httpx") -> Report:
    report = Report()
    async with build_client(cookies, transport_kind=transport_kind) as client:
        log.info("Cookie names loaded: %s", list(client.session.cookies.keys()))  # type: ignore[attr-defined]

        org_uuid = cookies.get("lastActiveOrg") or ""
        if not org_uuid:
            orgs = await _step(
                report, "list_organizations", client(ListOrganizations())
            )
            if not orgs:
                return report
            org_uuid = orgs[0].get("uuid", "")
        client.org_uuid = org_uuid
        report.add("pick_org_uuid", bool(org_uuid), org_uuid or "(empty)", 0)

        await _step(report, "get_profile", client.get_profile())
        await _step(report, "get_organization", client.get_organization())
        await _step(report, "get_subscription", client.get_subscription())
        await _step(report, "get_credits", client.get_credits())
        await _step(report, "get_styles", client.get_styles())
        await _step(report, "list_conversations", client.list_conversations(limit=5))

        conv_uuid = str(_uuid.uuid4())
        conv = await _step(
            report,
            "create_conversation",
            client.create_conversation(uuid=conv_uuid),
        )
        if conv is None:
            return report

        await _step(
            report,
            "send_message_short",
            client.send_message_and_collect(
                conv_uuid,
                "Reply with exactly the word: pong",
            ),
        )

        await _step(
            report,
            "send_message_followup",
            client.send_message_and_collect(
                conv_uuid,
                "Now reply with exactly the word: pang",
            ),
        )

        await _step(
            report,
            "get_conversation",
            client.get_conversation(conv_uuid, tree=True),
        )
        await _step(
            report,
            "generate_title",
            client.generate_title(conv_uuid, message_content="Reply pong"),
        )
        await _step(
            report,
            "update_conversation",
            client.update_conversation(conv_uuid, name="claude_lib renamed"),
        )
        await _step(
            report, "delete_conversation", client.delete_conversation(conv_uuid)
        )

    return report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--cookies",
        default=os.environ.get("CLAUDE_COOKIES", ""),
        help="Full claude.ai cookie string (key=val; key2=val2; ...). Must include sessionKey.",
    )
    p.add_argument(
        "--cookies-file",
        default="",
        help="Path to a file containing the full cookie string (one line).",
    )
    p.add_argument(
        "--session-key",
        default=os.environ.get("CLAUDE_SESSION_KEY", ""),
        help="Fallback: just sessionKey (no other cookies).",
    )
    p.add_argument(
        "--transport",
        default="aiohttp",
        choices=("aiohttp", "httpx", "http2"),
        help="Transport implementation (default aiohttp). http2 forces HTTP/2 over httpx.",
    )
    args = p.parse_args()

    raw_cookies = ""
    if args.cookies_file:
        raw_cookies = Path(args.cookies_file).read_text(encoding="utf-8").strip()
    elif args.cookies:
        raw_cookies = args.cookies

    if raw_cookies:
        cookies = parse_cookie_string(raw_cookies)
    elif args.session_key:
        cookies = {"sessionKey": args.session_key}
    else:
        print("Missing cookies. Pass --cookies / --cookies-file / --session-key.")
        return 2
    if "sessionKey" not in cookies:
        print("Cookie jar is missing required 'sessionKey'.")
        return 2

    try:
        report = asyncio.run(run(cookies, transport_kind=args.transport))
    except ClaudeAIError as exc:
        log.error("Top-level ClaudeAIError: %s", exc)
        return 1
    print(report.summary())
    return 0 if all(s.ok for s in report.steps) else 1


if __name__ == "__main__":
    sys.exit(main())
