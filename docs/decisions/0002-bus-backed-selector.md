# 0002 — Orchestrator selector reads from `LimitTracker`, not `client.session.limit_state`

**Date:** 2026-04-27
**Status:** accepted

## Context

`ClaudeOrchestrator` picks one of N clients per `send_message`. The natural selector criterion is rate-limit utilization (5h / 7d windows). The data source is the SSE `message_limit` event — already published on the bus as `LimitUpdatedEvent`.

The original `LeastUtilizationSelector` reached into `client.session.limit_state` directly. That works but couples the orchestrator's selection layer to `HttpSession`'s internal attribute name and lifecycle.

## Decision

The default selector is `BusBackedLeastUtilizationSelector(orchestrator.limits)`. The orchestrator subscribes a `LimitTracker` to `LimitUpdatedEvent` during `start()`; the tracker holds `dict[account_id → LimitSnapshot]`. The selector reads from the tracker.

The legacy `LeastUtilizationSelector` (reads from `client.session.limit_state`) is kept for callers who pass it explicitly.

## Alternatives considered

- **Keep `LeastUtilizationSelector` as default** — rejected: implicitly couples selection to one specific session impl. A future `RemoteSession` (e.g. SDK process talks to a sidecar) wouldn't have a `session.limit_state` attribute, but it would still publish `LimitUpdatedEvent` over the wire.
- **Push utilization into `client.metadata`** — rejected: yet another mutable surface to keep in sync. The bus is already doing the synchronization; reuse it.
- **Selector subscribes to events itself** — rejected: selectors are async-pickable functions in spirit. Adding lifecycle (subscribe/unsubscribe) to them complicates `pick()` callers and forces the selector to outlive its subscription.

## Consequences

- The first `pick()` after orchestrator startup gives every client max priority (utilization 0.0) — the tracker only fills as `LimitUpdatedEvent`s arrive. For homogeneous clients this is fine; for clients with very different historical loads, a brief warmup is unavoidable without persisting tracker state. Out of scope for now.
- `LimitTracker.get(unknown_id)` returns a fresh `LimitSnapshot()` (score=0). Don't change that contract — the selector relies on it for «no data → eligible» semantics.
- `LeastInFlightSelector(MessageMetrics)` follows the same pattern — bulkhead-style routing reading `metrics.in_flight(account_id)`.
- Backwards compat: if a user passes a custom selector that touches `client.session`, it still works. Default users get the bus-backed one.

Trigger to revisit: if we add a third orthogonal axis (cost? latency?) and want them composed, factor selectors into a chain rather than adding more `BusBacked*` variants.
