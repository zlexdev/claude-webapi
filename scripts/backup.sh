#!/usr/bin/env bash
# Dump the gateway Postgres database to ./backups/<timestamp>.dump
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
load_env
[ "${CLAUDE_GATEWAY_DB:-postgres}" = "postgres" ] || { warn "DB is not postgres — nothing to back up"; exit 0; }
command -v pg_dump >/dev/null || die "pg_dump not found"
mkdir -p "${ROOT}/backups"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${ROOT}/backups/${STAMP}.dump"
# Strip the +asyncpg driver suffix for libpq tools.
DSN="${CLAUDE_GATEWAY_DATABASE_URL/+asyncpg/}"
info "dumping to ${OUT}"
pg_dump --format=custom --no-owner --dbname="${DSN}" --file="${OUT}"
ok "backup written: ${OUT}"
