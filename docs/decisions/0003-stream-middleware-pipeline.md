# 0003 — `HttpSession.stream` runs `http_middleware` with a no-op terminal

**Date:** 2026-04-27
**Status:** accepted

## Context

`HttpSession` has two send paths — `request()` for buffered responses and `stream()` for SSE. Both build a `TransportRequest` from the same envelope but only `request()` ran the middleware chain. `stream()` called `transport.stream(request)` directly, bypassing `BrowserHeadersMiddleware`, `RetryMiddleware`, `RateLimitMiddleware`, and any user-added middleware.

This bit us hard: claude.ai's `/completion` endpoint requires a full Chrome-shaped header set + a per-conversation `referer`. With those headers missing, Cloudflare returned `403 "Just a moment…"`. The non-stream endpoints worked because they DID run the middleware. The bug presented as a streaming-only Cloudflare block — looked like an anti-bot problem, but was a missing pipeline.

## Decision

`HttpSession.stream()` runs `http_middleware.chain(noop_terminal)` to mutate `request.headers` BEFORE calling `transport.stream(request)`. The terminal returns a synthetic `TransportResponse(status_code=0, ...)` so `LoggingMiddleware` and `RetryMiddleware` see a no-op «success» and don't double-send.

## Alternatives considered

- **Add a separate `stream_middleware` chain** — rejected: forces users to register the same headers twice (once for HTTP, once for stream). Most middleware is shape-agnostic.
- **Make middleware a pure header-mutation phase, separate from sending** — bigger refactor. Would split `Middleware[E,R]` into `RequestMiddleware` + `ResponseMiddleware`. Worth considering eventually; not worth blocking the bug fix.
- **Have `transport.stream` accept a list of middlewares** — rejected: middleware lives at the session level, not the transport level. Pushing it down inverts the dependency.

## Consequences

- `RetryMiddleware` sees status 0 on the no-op pass and returns immediately. It's effectively a no-op for streams. Acceptable — SSE retry semantics differ anyway (mid-stream failure can't be silently retried without re-emitting half the tokens).
- `LoggingMiddleware` logs the no-op «request» as completed with status 0. Users grepping logs see entries with `status=0` for streams.
- Custom middleware that ASSUMES `await handler(...)` actually sends will malfunction on streams.
- `SendMessage.build_params` now also sets `referer: https://claude.ai/chat/{conv_uuid}` in the envelope's `headers` field — the chain merges this with the middleware's static `referer`, with the method's value winning (precedence: method headers > middleware setdefault).

Trigger to revisit: if we add async-iterating middleware (e.g. transformers per chunk), we'll need a real `stream_middleware` chain. The no-op terminal is fine for header injection only.
