#!/usr/bin/env bash
# Start the gateway as it runs in production (server chosen by CLAUDE_GATEWAY_SERVER).
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
load_env
[ -x "${PY}" ] || die "venv missing — run scripts/install.sh first"
info "starting claude-gateway (${CLAUDE_GATEWAY_SERVER:-fastapi}) on ${CLAUDE_GATEWAY_HOST:-0.0.0.0}:${CLAUDE_GATEWAY_PORT:-8081}"
exec "${PY}" -m gateway
