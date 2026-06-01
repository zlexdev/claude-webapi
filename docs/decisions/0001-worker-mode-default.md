# 0001 — Default `MemoryEventBus` mode is `worker`, not `inline`

**Date:** 2026-04-27
**Status:** accepted

## Context

Events are emitted from the SSE iterator (`HttpSession._iterate_stream`) and from the proxy failure path (`HttpxTransport._on_failure`). Producers are latency-sensitive — every microsecond inside `_iterate_stream` delays the next user-visible token. Handlers, in contrast, do bookkeeping (metrics, blacklists, limits) that can run with up to a few seconds of lag without anyone noticing.

The previous bus ran handlers synchronously: `await bus.publish(event)` resolved only after every matched handler finished `gather`-ed. A slow / blocking handler stalled the producing task.

## Decision

`MemoryEventBus(mode="worker")` is the default. `publish()` enqueues into `asyncio.Queue` and returns; N background tasks (`EventWorker`) consume and dispatch. `mode="inline"` is opt-in for tests and for cases where ordering relative to `publish()` matters.

## Alternatives considered

- **Keep `inline` as default** — rejected: any test that adds a `time.sleep`-equivalent in a handler immediately tanks production stream throughput.
- **Make every handler `asyncio.create_task`-ed inside `publish()`** — rejected: no backpressure, no DLQ, no observable failure path. A handler exception became a logged warning that nothing else ever saw.
- **Producer-only pool (`asyncio.create_task(handler(...))`) without a queue** — rejected: same as above, plus tasks GC'd if no one held a reference. The current `EventWorker` queue is the reference holder.

## Consequences

- `await bus.publish(event)` does NOT mean «handlers ran». Tests must `await bus.flush()` before asserting on tracker state.
- Handler failures don't propagate to the publisher — they go to `store.dead_letter`. Operators must look at DLQ, not at the producer's exception path.
- Worker uses an `asyncio.Queue` — bus is loop-bound. Cross-loop usage now raises `RuntimeError` instead of silently working in `inline` mode.
- `inline` mode remains supported and tested; orchestrator handler tests use it because they need ordering guarantees.

Trigger to revisit: if we ever need handlers to run in the producer's transaction (e.g. block sending the next message until a metric is recorded), reconsider whether worker mode is right for that path.
