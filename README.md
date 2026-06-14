# claude-webapi

**English** · [Русский](README.ru.md)

Async Python SDK + multi-account orchestrator for the **claude.ai** web app,
reverse-engineered from captured traffic. Streams real SSE completions, tracks
rate-limit windows, and fans bulk/batch work across a pool of accounts. Typed
end-to-end (`pydantic` v2), cookie-auth, no bearer tokens.

> ⚠️ Automating claude.ai accounts is against Anthropic's ToS — use only your
> own accounts, at your own risk. No warranty.

> 🛠️ This project is **almost entirely vibecoded**.

## Layout

- `claude_ai/` — SDK package. Entry: `ClaudeAIClient` (single account), `ClaudeOrchestrator` (pool).
- `claude_ai/methods/` — one file per endpoint (`BaseMethod[Params, R]` legacy, `RequestMethod` field-style).
- `claude_ai/middleware/` — request pipeline (logging → rate-limit → retry).
- `claude_ai/bus/` — event bus, worker / inline modes, `Null/Memory/Redis/Mongo` stores.
- `claude_ai/orchestrator/` — multi-client routing, bulk executor, resumable batch runner.
- `claude_ai/storage/` — `cache/` (TTL), `cookies/` (auth), `kv/` (persistent state).
- `claude_ai/streaming/`, `session/`, `transport/`, `auth/`, `events/`, `models/`, `enums/` — supporting layers.

## Stack

- Python 3.11+
- `aiohttp` (default HTTP transport) / `httpx` (alternate via `CLAUDE_AI_TRANSPORT=httpx`)
- `pydantic` v2, `pydantic-settings`

## Install

```bash
pip install "claude-webapi @ git+https://github.com/zlexdev/claude-webapi.git"
# with persistence + transport backends:
pip install "claude-webapi[all] @ git+https://github.com/zlexdev/claude-webapi.git"
```

Optional extras: `sqlite`, `mongo`, `file`, `redis`, `all`, `dev`.

## Quickstart — one account

```python
import asyncio
from claude_ai import ClaudeAIClient, HttpSession

async def main() -> None:
    session = HttpSession(account_id="me", cookies={"sessionKey": "sk-ant-sid02-..."})
    async with ClaudeAIClient(account_id="me", session=session) as client:
        client.org_uuid = "..."
        result = await client.send_message_and_collect(conv_uuid="...", prompt="ping")
        print(result.text)

asyncio.run(main())
```

> **Cloudflare (403 `cf-mitigated: challenge`).** `sessionKey` alone is not enough — `claude.ai` gates the API behind Cloudflare. Provide the **full cookie jar** harvested from a browser that passes the challenge (`sessionKey` + **`cf_clearance`** + `__cf_bm` + `_cfuvid`), and make sure `CLAUDE_AI_USER_AGENT` matches that browser (default = Chrome 148) — CF binds `cf_clearance` to `(IP, User-Agent)`. No TLS impersonation / `curl_cffi` is needed. `cf_clearance`/`__cf_bm` are short-lived; re-harvest when they expire.

## Account pool (orchestrator)

```python
from claude_ai import ClaudeAIClient, ClaudeOrchestrator, AccountTier, HttpSession
from claude_ai.storage.kv.sqlite import AioSqliteStorage

orch = ClaudeOrchestrator(storage=AioSqliteStorage("pool.db"))   # persistent state
await orch.add(ClaudeAIClient("a1", session=HttpSession("a1", cookies={...})), tier=AccountTier.PRO)
await orch.add(ClaudeAIClient("a2", session=HttpSession("a2", cookies={...})), tier=AccountTier.FREE)

# least-utilised, rate-limit-aware, sticky-per-conversation routing:
events = await orch.send_message("Hi", conv_uuid="conv-1")
```

The pool parks rate-limited accounts until their window resets, quarantines dead
sessions (optional `relogin=` hook), and pins each conversation to its account
(`affinity`).

## Bulk fan-out

```python
results = await orch.map(prompts, fn, concurrency_per_account=2)
# per-account bulkhead + backpressure + cross-account failover; failures land in
# the executor's dead_letters.
```

## Resumable batch jobs

```python
runner = orch.batch_runner()                       # persists via the pool's storage
job = await runner.run("nightly-2026-05-31", prompts, fn)
# crash mid-run? call run() with the same job_id — DONE items are skipped,
# the rest retried.
```

`BaseBatchStore` is the extension point — subclass it to persist into a project's
own Postgres / queue instead of the default `storage/kv` backend.

## Development

```bash
pip install -e ".[dev,all]"
ruff check claude_ai && mypy claude_ai && python -m pytest -k "not live"
```

Live integration tests: drop a one-line cookie string at `tests/.cookies.local`
(must include `sessionKey`). Offline: `pytest -k "not live"`.

## Status

Private. No support, no warranty. Reverse-engineered from claude.ai web traffic.

---

## HTTP Gateway (`gateway/`)

A self-hosted, OpenAI-compatible HTTP server in front of the SDK. Talk to claude.ai
with `curl` or the `openai` SDK; manage chats; reach any SDK method through one
generic endpoint. Three interchangeable frontends (FastAPI / Litestar / aiohttp) for
different load tiers share one framework-agnostic core.

### Install & run

**Linux / macOS** — one command surface via `make` (or call the scripts directly):

```bash
make install        # venv + deps + .env seed + schema bootstrap (idempotent)
# edit .env: set CLAUDE_GATEWAY_ADMIN_TOKEN (memory mode needs nothing else)
make run            # start the gateway  (== scripts/run.sh)
```

`make help` lists every command: `install run update test smoke provision backup
restore lint type clean`. Flags pass through, e.g. `make install ARGS=--dry-run`.

**Windows** (no `make`; use the `.bat` mirrors):

```bat
scripts\install.bat                REM venv + deps + .env seed + schema
REM edit .env: set CLAUDE_GATEWAY_ADMIN_TOKEN
scripts\run.bat                    REM start the gateway
```

**Docker** (gateway + Postgres):

```bash
cp .env.example .env               # set CLAUDE_GATEWAY_ADMIN_TOKEN (+ optional POSTGRES_PASSWORD)
docker compose up --build          # gateway on :8081, Postgres with a healthcheck
```

**systemd** (bare-metal): `deploy/claude-gateway.service` — copy to
`/etc/systemd/system/`, adjust paths, `systemctl enable --now claude-gateway`.
`scripts/update.sh` does a health-gated redeploy and auto-rolls-back on a failed
`/health` probe.

Config keys live in `.env` (see `.env.example`); defaults boot in `memory` mode.

### Onboard an account → key (admin)

One command (session key from env / stdin, never argv — it's a secret):

```bash
CLAUDE_SESSION_KEY=sk-ant-sid02-... scripts/provision.sh --org <uuid> --name cli
# Windows:  $env:CLAUDE_SESSION_KEY="sk-ant-sid02-..."; scripts\provision.ps1 -Name cli
# -> OK  API key (shown once): sk-...
```

Or the raw endpoint it wraps:

```bash
curl -X POST localhost:8081/system/keys/generate \
  -H "X-Admin-Token: $CLAUDE_GATEWAY_ADMIN_TOKEN" \
  -d '{"cookies": {"sessionKey": "sk-ant-sid01-...", "cf_clearance": "...", "__cf_bm": "...", "_cfuvid": "..."}, "org_uuid": "...", "name": "cli", "user_agent": "Mozilla/5.0 ... Chrome/148.0.0.0 ..."}'
# -> { "key": "sk-...", "info": { ... } }   (the key is shown once)
```

**Lifecycle: provision → use → refresh.** An account must exist *before* a key can serve
traffic — the OpenAI client only ever sends `Authorization: Bearer sk-...`; the cookies
live server-side and are attached when the key resolves to its account. So the order is
always: (1) provision the account (`/system/accounts/create`, or the one-shot
`/system/keys/generate` with `cookies`), then (2) use the returned key.

> **Cloudflare:** include the full cookie jar (`cf_clearance` + `__cf_bm` + `_cfuvid`, not just `sessionKey`) and provide a `user_agent` matching the browser those cookies came from — otherwise org-scoped calls return `403 cf-mitigated: challenge`. The cookies are short-lived; refresh them (below) when they expire.

> **Per-account User-Agent.** `cf_clearance` is bound to `(egress IP, User-Agent)`. The per-account `user_agent` field lets one gateway pool jars captured under different browsers; omit it to fall back to the process-global `CLAUDE_AI_USER_AGENT` (default Chrome 148).

> **Cookies at rest.** Set `CLAUDE_GATEWAY_COOKIE_ENCRYPTION_KEY` to a urlsafe-base64 Fernet key (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`) to Fernet-encrypt every jar in the Postgres `data` column. Unset → plaintext JSON. Jars stored before a key was set keep loading and migrate to ciphertext the next time the account is saved.

### Refresh cookies (no re-provision)

`cf_clearance` / `__cf_bm` expire in hours. Refresh a live account's CF session in place
instead of minting a new account + key — the pooled client is rebuilt with the new jar
immediately, keeping the same `account_id` and existing keys:

```bash
curl -X PATCH localhost:8081/system/accounts/acc_<id>/cookies \
  -H "X-Admin-Token: $CLAUDE_GATEWAY_ADMIN_TOKEN" \
  -d '{"cookies": {"sessionKey": "...", "cf_clearance": "...", "__cf_bm": "...", "_cfuvid": "..."}, "user_agent": "Mozilla/5.0 ..."}'
# -> { "account_id": "acc_<id>", "user_agent": "...", ... }   (cookies are never echoed back)
```

`user_agent` is optional on refresh (omit to keep the stored one). Re-provision a fresh
account only when the jar is unrecoverable.

### Smoke test (end-to-end, live)

Boots an ephemeral in-memory gateway, provisions a real account, and checks every
surface. Exit 0 only if all gateway-wiring checks pass; upstream (claude.ai)
failures are reported separately.

```bash
CLAUDE_SMOKE_SESSION_KEY=sk-ant-sid02-... make smoke          # or scripts/smoke.sh
# Windows:  $env:CLAUDE_SMOKE_SESSION_KEY="sk-ant-sid02-..."; scripts\smoke.ps1
```

### Use it

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8081/v1", api_key="sk-...")
print(client.chat.completions.create(
    model="gemini-3.5-flash-thinking",                # alias → claude model
    messages=[{"role": "user", "content": "Explain quantum computing"}],
).choices[0].message.content)
```

### Tool / function calling

Pass an OpenAI `tools` array. A function whose name is in the native registry
(`web_search`) is proxied into claude.ai and run server-side — its result folds into
the answer text. Any other function is prompt-emulated: the gateway returns
`finish_reason="tool_calls"` for the caller to execute and feed back via a
`role:"tool"` message. With custom tools, `stream=true` buffers and emits one
consolidated `tool_calls` chunk.

> ⚠️ **Maturity, verified live against claude.ai:** native tools (`web_search`) work.
> Custom function-calling is **best-effort** — claude.ai's hosted model has a strong
> system prompt about its real toolset and routinely refuses the injected
> `<tool_call>` contract (even with `tool_choice:"required"` it often answers
> normally, `tool_calls:null`). The gateway's parsing/mapping is correct and
> unit-tested; the gap is model compliance. Treat custom tools as opportunistic.

Surfaces: `POST /v1/chat/completions` (+`stream`, +`tools`), `GET /v1/models`,
`POST /v1/prompt` (`{"text": ...}`), `GET /v1/chats/list`,
`GET /v1/chats/{id}/messages` (paginated), `POST /v1/chats/{id}/send`,
`POST /v1/methods/invoke` (any SDK method), `GET /v1/methods/list` (auto-docs, also
`gateway/METHODS.md`). Admin under `/system/*`.

Auth: `Authorization: Bearer sk-...` (one key ↔ one account). Storage: PostgreSQL via
SQLAlchemy (`CLAUDE_GATEWAY_DB=memory` for dev/tests). Ops: `make <cmd>` /
`scripts/{install,update,run,backup,restore,rollback,provision,smoke}.sh` on POSIX,
`scripts/{install,run,update}.bat` + `{provision,smoke}.ps1` on Windows, plus
`Dockerfile` / `docker-compose.yml` / `deploy/claude-gateway.service`.
