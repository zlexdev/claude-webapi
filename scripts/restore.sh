#!/usr/bin/env bash
# Restore the gateway Postgres database from a dump: scripts/restore.sh <file.dump>
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
load_env
[ "${CLAUDE_GATEWAY_DB:-postgres}" = "postgres" ] || die "DB is not postgres"
command -v pg_restore >/dev/null || die "pg_restore not found"
FILE="${1:-}"
[ -f "${FILE}" ] || die "usage: restore.sh <path-to-.dump>"
DSN="${CLAUDE_GATEWAY_DATABASE_URL/+asyncpg/}"
warn "restoring ${FILE} into ${DSN} (existing data may be overwritten)"
pg_restore --clean --if-exists --no-owner --dbname="${DSN}" "${FILE}"
ok "restore complete"
