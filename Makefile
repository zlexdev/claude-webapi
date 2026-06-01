# claude-gateway — command surface. POSIX hosts; Windows uses scripts/*.bat.
.DEFAULT_GOAL := help
SHELL := /usr/bin/env bash
PY := .venv/bin/python

.PHONY: help install run update test smoke backup restore provision lint type clean

help: ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## venv + deps + .env seed + schema (idempotent)
	bash scripts/install.sh $(ARGS)

run: ## start the gateway (server from CLAUDE_GATEWAY_SERVER)
	bash scripts/run.sh

update: ## git pull + reinstall + migrate + health-gated restart
	bash scripts/update.sh $(ARGS)

test: ## run the gateway test suite
	$(PY) -m pytest -q tests/gateway

smoke: ## end-to-end live smoke (needs CLAUDE_SMOKE_SESSION_KEY)
	bash scripts/smoke.sh

provision: ## onboard an account -> mint a key (needs CLAUDE_SESSION_KEY)
	bash scripts/provision.sh $(ARGS)

backup: ## dump the postgres database to ./backups
	bash scripts/backup.sh

restore: ## restore a postgres dump (ARGS=<dump-file>)
	bash scripts/restore.sh $(ARGS)

lint: ## ruff check the gateway package
	$(PY) -m ruff check gateway

type: ## mypy --strict the gateway package
	$(PY) -m mypy gateway

clean: ## remove caches (keeps .venv)
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .mypy_cache
