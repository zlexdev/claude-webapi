# claude-webapi

[English](README.md) · **Русский**

Асинхронный Python SDK + мульти-аккаунт оркестратор для веб-приложения **claude.ai**,
реверс-инженеренный из перехваченного трафика. Стримит настоящие SSE-ответы, отслеживает
окна рейт-лимитов и распределяет массовую/батч-работу по пулу аккаунтов. Полностью
типизирован (`pydantic` v2), авторизация по кукам, без bearer-токенов.

> ⚠️ Автоматизация аккаунтов claude.ai нарушает ToS Anthropic — используй только
> свои аккаунты и на свой риск. Без каких-либо гарантий.

> 🛠️ Проект **почти полностью vibecoded**.

## Структура

- `claude_ai/` — пакет SDK. Точка входа: `ClaudeAIClient` (один аккаунт), `ClaudeOrchestrator` (пул).
- `claude_ai/methods/` — по одному файлу на эндпоинт (`BaseMethod[Params, R]` — legacy, `RequestMethod` — field-style).
- `claude_ai/middleware/` — конвейер запроса (логирование → рейт-лимит → ретраи).
- `claude_ai/bus/` — шина событий, режимы worker / inline, хранилища `Null/Memory/Redis/Mongo`.
- `claude_ai/orchestrator/` — маршрутизация между клиентами, исполнитель массовых задач, возобновляемый батч-раннер.
- `claude_ai/storage/` — `cache/` (TTL), `cookies/` (авторизация), `kv/` (персистентное состояние).
- `claude_ai/streaming/`, `session/`, `transport/`, `auth/`, `events/`, `models/`, `enums/` — вспомогательные слои.

## Стек

- Python 3.11+
- `aiohttp` (HTTP-транспорт по умолчанию) / `httpx` (альтернатива через `CLAUDE_AI_TRANSPORT=httpx`)
- `pydantic` v2, `pydantic-settings`

## Установка

```bash
pip install "claude-webapi @ git+https://github.com/zlexdev/claude-webapi.git"
# с персистентностью + транспортными бэкендами:
pip install "claude-webapi[all] @ git+https://github.com/zlexdev/claude-webapi.git"
```

Опциональные extras: `sqlite`, `mongo`, `file`, `redis`, `all`, `dev`.

## Быстрый старт — один аккаунт

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

> **Cloudflare (403 `cf-mitigated: challenge`).** Одного `sessionKey` недостаточно — `claude.ai` закрывает API за Cloudflare. Передавай **полный набор кук**, снятый с браузера, который прошёл challenge (`sessionKey` + **`cf_clearance`** + `__cf_bm` + `_cfuvid`), и убедись, что `CLAUDE_AI_USER_AGENT` совпадает с тем браузером (по умолчанию = Chrome 148) — CF привязывает `cf_clearance` к паре `(IP, User-Agent)`. TLS-имперсонизация / `curl_cffi` не нужны. `cf_clearance`/`__cf_bm` живут недолго — пересобирай, когда истекут.

## Пул аккаунтов (оркестратор)

```python
from claude_ai import ClaudeAIClient, ClaudeOrchestrator, AccountTier, HttpSession
from claude_ai.storage.kv.sqlite import AioSqliteStorage

orch = ClaudeOrchestrator(storage=AioSqliteStorage("pool.db"))   # персистентное состояние
await orch.add(ClaudeAIClient("a1", session=HttpSession("a1", cookies={...})), tier=AccountTier.PRO)
await orch.add(ClaudeAIClient("a2", session=HttpSession("a2", cookies={...})), tier=AccountTier.FREE)

# маршрутизация: наименее загруженный, с учётом рейт-лимитов, sticky на разговор:
events = await orch.send_message("Hi", conv_uuid="conv-1")
```

Пул паркует зарейт-лимиченные аккаунты до сброса их окна, изолирует мёртвые
сессии (опциональный хук `relogin=`) и закрепляет каждый разговор за его аккаунтом
(`affinity`).

## Массовый fan-out

```python
results = await orch.map(prompts, fn, concurrency_per_account=2)
# bulkhead на аккаунт + backpressure + межаккаунтный failover; сбои попадают
# в dead_letters исполнителя.
```

## Возобновляемые батч-задачи

```python
runner = orch.batch_runner()                       # персистит через storage пула
job = await runner.run("nightly-2026-05-31", prompts, fn)
# упал на середине? вызови run() с тем же job_id — items в статусе DONE пропускаются,
# остальные ретраятся.
```

`BaseBatchStore` — точка расширения: отнаследуйся от него, чтобы персистить в
собственный Postgres / очередь проекта вместо дефолтного бэкенда `storage/kv`.

## Разработка

```bash
pip install -e ".[dev,all]"
ruff check claude_ai && mypy claude_ai && python -m pytest -k "not live"
```

Live-интеграционные тесты: положи однострочную куку-строку в `tests/.cookies.local`
(должна содержать `sessionKey`). Оффлайн: `pytest -k "not live"`.

## Статус

Приватный. Без поддержки и гарантий. Реверс-инженеринг из веб-трафика claude.ai.

---

## HTTP-шлюз (`gateway/`)

Самохостящийся OpenAI-совместимый HTTP-сервер перед SDK. Общайся с claude.ai
через `curl` или `openai` SDK; управляй чатами; дотянись до любого метода SDK через один
универсальный эндпоинт. Три взаимозаменяемых фронтенда (FastAPI / Litestar / aiohttp) под
разные уровни нагрузки используют одно framework-agnostic ядро.

### Установка и запуск

**Linux / macOS** — единый интерфейс команд через `make` (или вызывай скрипты напрямую):

```bash
make install        # venv + зависимости + сид .env + bootstrap схемы (идемпотентно)
# отредактируй .env: задай CLAUDE_GATEWAY_ADMIN_TOKEN (для memory-режима больше ничего не нужно)
make run            # запустить шлюз  (== scripts/run.sh)
```

`make help` перечисляет все команды: `install run update test smoke provision backup
restore lint type clean`. Флаги пробрасываются, например `make install ARGS=--dry-run`.

**Windows** (без `make`; используй `.bat`-зеркала):

```bat
scripts\install.bat                REM venv + зависимости + сид .env + схема
REM отредактируй .env: задай CLAUDE_GATEWAY_ADMIN_TOKEN
scripts\run.bat                    REM запустить шлюз
```

**Docker** (шлюз + Postgres):

```bash
cp .env.example .env               # задай CLAUDE_GATEWAY_ADMIN_TOKEN (+ опц. POSTGRES_PASSWORD)
docker compose up --build          # шлюз на :8081, Postgres с healthcheck
```

**systemd** (bare-metal): `deploy/claude-gateway.service` — скопируй в
`/etc/systemd/system/`, поправь пути, `systemctl enable --now claude-gateway`.
`scripts/update.sh` делает передеплой с health-gate и автоматически откатывается при
провале пробы `/health`.

Ключи конфигурации живут в `.env` (см. `.env.example`); по умолчанию загрузка в режиме `memory`.

### Подключить аккаунт → ключ (админ)

Одна команда (session key из env / stdin, никогда не из argv — это секрет):

```bash
CLAUDE_SESSION_KEY=sk-ant-sid02-... scripts/provision.sh --org <uuid> --name cli
# Windows:  $env:CLAUDE_SESSION_KEY="sk-ant-sid02-..."; scripts\provision.ps1 -Name cli
# -> OK  API-ключ (показывается один раз): sk-...
```

Или сырой эндпоинт, который она оборачивает:

```bash
curl -X POST localhost:8081/system/keys/generate \
  -H "X-Admin-Token: $CLAUDE_GATEWAY_ADMIN_TOKEN" \
  -d '{"cookies": {"sessionKey": "sk-ant-sid01-...", "cf_clearance": "...", "__cf_bm": "...", "_cfuvid": "..."}, "org_uuid": "...", "name": "cli", "user_agent": "Mozilla/5.0 ... Chrome/148.0.0.0 ..."}'
# -> { "key": "sk-...", "info": { ... } }   (ключ показывается один раз)
```

**Жизненный цикл: provision → use → refresh.** Аккаунт должен существовать *до* того, как
ключ начнёт обслуживать трафик — OpenAI-клиент всегда шлёт только `Authorization: Bearer sk-...`;
куки живут на сервере и подставляются, когда ключ резолвится в свой аккаунт. Поэтому порядок
всегда такой: (1) подключить аккаунт (`/system/accounts/create` или one-shot
`/system/keys/generate` с `cookies`), затем (2) использовать возвращённый ключ.

> **Cloudflare:** передавай полный набор кук (`cf_clearance` + `__cf_bm` + `_cfuvid`, не только `sessionKey`) и указывай `user_agent`, совпадающий с браузером, откуда эти куки сняты — иначе org-scoped вызовы вернут `403 cf-mitigated: challenge`. Куки живут недолго; обновляй их (ниже), когда истекут.

> **User-Agent на аккаунт.** `cf_clearance` привязан к паре `(egress IP, User-Agent)`. Поле `user_agent` на аккаунт позволяет одному шлюзу держать пул наборов кук, снятых под разными браузерами; опусти его, чтобы откатиться на процесс-глобальный `CLAUDE_AI_USER_AGENT` (по умолчанию Chrome 148).

> **Куки на диске (at rest).** Задай `CLAUDE_GATEWAY_COOKIE_ENCRYPTION_KEY` как urlsafe-base64 Fernet-ключ (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`), чтобы Fernet-шифровать каждый набор кук в колонке `data` Postgres. Не задан → JSON в открытом виде. Наборы, сохранённые до установки ключа, продолжают загружаться и мигрируют в шифртекст при следующем сохранении аккаунта.

### Обновление кук (без переподключения)

`cf_clearance` / `__cf_bm` истекают за часы. Обнови CF-сессию живого аккаунта на месте,
вместо того чтобы создавать новый аккаунт + ключ — клиент в пуле немедленно пересобирается
с новым набором кук, сохраняя тот же `account_id` и существующие ключи:

```bash
curl -X PATCH localhost:8081/system/accounts/acc_<id>/cookies \
  -H "X-Admin-Token: $CLAUDE_GATEWAY_ADMIN_TOKEN" \
  -d '{"cookies": {"sessionKey": "...", "cf_clearance": "...", "__cf_bm": "...", "_cfuvid": "..."}, "user_agent": "Mozilla/5.0 ..."}'
# -> { "account_id": "acc_<id>", "user_agent": "...", ... }   (куки никогда не возвращаются в ответе)
```

`user_agent` на refresh опционален (опусти, чтобы сохранить уже хранящийся). Переподключай
свежий аккаунт только когда набор кук невосстановим.

### Smoke-тест (end-to-end, live)

Поднимает эфемерный in-memory шлюз, подключает реальный аккаунт и проверяет каждую
поверхность. Exit 0 только если все проверки обвязки шлюза прошли; сбои upstream (claude.ai)
репортятся отдельно.

```bash
CLAUDE_SMOKE_SESSION_KEY=sk-ant-sid02-... make smoke          # или scripts/smoke.sh
# Windows:  $env:CLAUDE_SMOKE_SESSION_KEY="sk-ant-sid02-..."; scripts\smoke.ps1
```

### Использование

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8081/v1", api_key="sk-...")
print(client.chat.completions.create(
    model="gemini-3.5-flash-thinking",                # алиас → модель claude
    messages=[{"role": "user", "content": "Explain quantum computing"}],
).choices[0].message.content)
```

### Вызов инструментов / функций

Передай OpenAI-массив `tools`. Функция, чьё имя есть в нативном реестре
(`web_search`), проксируется в claude.ai и выполняется на сервере — её результат вплетается
в текст ответа. Любая другая функция эмулируется через промпт: шлюз возвращает
`finish_reason="tool_calls"`, чтобы вызывающая сторона выполнила её и вернула результат через
сообщение `role:"tool"`. С кастомными инструментами `stream=true` буферизует и выдаёт один
консолидированный `tool_calls`-чанк.

> ⚠️ **Зрелость, проверено вживую против claude.ai:** нативные инструменты (`web_search`) работают.
> Кастомный function-calling — **best-effort**: у хостящейся модели claude.ai сильный
> системный промпт про её реальный набор инструментов, и она регулярно отказывается от
> внедрённого контракта `<tool_call>` (даже с `tool_choice:"required"` часто отвечает
> обычным текстом, `tool_calls:null`). Парсинг/маппинг шлюза корректны и покрыты
> юнит-тестами; разрыв — в комплаенсе модели. Относись к кастомным инструментам как к оппортунистическим.

Поверхности: `POST /v1/chat/completions` (+`stream`, +`tools`), `GET /v1/models`,
`POST /v1/prompt` (`{"text": ...}`), `GET /v1/chats/list`,
`GET /v1/chats/{id}/messages` (с пагинацией), `POST /v1/chats/{id}/send`,
`POST /v1/methods/invoke` (любой метод SDK), `GET /v1/methods/list` (авто-доки, также
`gateway/METHODS.md`). Админка под `/system/*`.

Авторизация: `Authorization: Bearer sk-...` (один ключ ↔ один аккаунт). Хранилище: PostgreSQL через
SQLAlchemy (`CLAUDE_GATEWAY_DB=memory` для разработки/тестов). Ops: `make <cmd>` /
`scripts/{install,update,run,backup,restore,rollback,provision,smoke}.sh` на POSIX,
`scripts/{install,run,update}.bat` + `{provision,smoke}.ps1` на Windows, плюс
`Dockerfile` / `docker-compose.yml` / `deploy/claude-gateway.service`.
