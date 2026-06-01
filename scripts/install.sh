#!/usr/bin/env bash
# Fresh install on a clean host: venv, deps, env seed, schema bootstrap. Idempotent.
# Flags: --dry-run (print, don't mutate), --non-interactive, --reset.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
parse_flags "$@"

command -v python3 >/dev/null || die "python3 not found (need >= 3.11)" 2
python3 -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 11) else 1)' \
  || die "python >= 3.11 required" 2

info "creating virtualenv (idempotent)"
[ -d "${VENV}" ] || run python3 -m venv "${VENV}"
run "${PY}" -m pip install --quiet --upgrade pip
info "installing gateway + dependencies"
run "${PY}" -m pip install --quiet -e "${ROOT}[gateway]"

if [ ! -f "${ROOT}/.env" ]; then
  run cp "${ROOT}/.env.example" "${ROOT}/.env"
  # Default seed is DB=memory + empty ADMIN_TOKEN. Postgres needs manual edits;
  # memory mode only needs an ADMIN_TOKEN, so we let the operator continue.
  if grep -qE '^CLAUDE_GATEWAY_DB=postgres' "${ROOT}/.env"; then
    die "wrote .env — set CLAUDE_GATEWAY_ADMIN_TOKEN + DATABASE_URL, then re-run" 1
  fi
  warn "wrote a starter .env (memory mode) — set CLAUDE_GATEWAY_ADMIN_TOKEN before running"
fi
[ "${DRY}" = "1" ] || load_env

if [ "${DRY}" != "1" ] && [ "${CLAUDE_GATEWAY_DB:-memory}" = "postgres" ]; then
  info "verifying database connectivity + applying schema"
  "${PY}" - <<'PYEOF'
import asyncio
from gateway.shared.config import GatewaySettings
from gateway.shared.db.engine import Database
async def main() -> None:
    s = GatewaySettings()
    db = Database(s.database_url)
    await db.create_all()
    await db.close()
    print("schema ensured")
asyncio.run(main())
PYEOF
fi
ok "install complete — start with: make run  (or scripts/run.sh)"
