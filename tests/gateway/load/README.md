# Load tests

Baseline load profile for the gateway's three hot paths.

## Run

```bash
pip install locust
CLAUDE_GATEWAY_KEY=sk-... locust -f tests/gateway/load/locustfile.py \
    --host http://localhost:8081 --users 50 --spawn-rate 10 --run-time 2m --headless
```

Run once per server tier (`CLAUDE_GATEWAY_SERVER=fastapi|litestar|aiohttp`) to compare.

## Baseline (fill in after the first run)

| Server | Users | req/s | p95 (ms) | error % |
|---|---|---|---|---|
| fastapi  | 50 | _TBD_ | _TBD_ | _TBD_ |
| litestar | 50 | _TBD_ | _TBD_ | _TBD_ |
| aiohttp  | 50 | _TBD_ | _TBD_ | _TBD_ |

> Latency is dominated by the upstream claude.ai round-trip, not the gateway. The
> server-tier comparison isolates framework overhead; expect them within noise unless
> you bypass the upstream (mock account) to measure the gateway alone.
