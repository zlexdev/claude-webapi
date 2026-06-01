#!/usr/bin/env bash
# Pull + redeploy with a health gate: fetch code, reinstall, migrate (additive),
# restart, probe /health. On probe failure: auto-rollback to the recorded rev.
# Flags: --dry-run (print, don't mutate).
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
parse_flags "$@"
load_env

REV_FILE="${ROOT}/.last_deploy_rev"
HEALTH_URL="http://${CLAUDE_GATEWAY_HOST:-127.0.0.1}:${CLAUDE_GATEWAY_PORT:-8081}/health"
# 0.0.0.0 is a bind address, not a connect address.
[ "${CLAUDE_GATEWAY_HOST:-}" = "0.0.0.0" ] && HEALTH_URL="http://127.0.0.1:${CLAUDE_GATEWAY_PORT:-8081}/health"

CURRENT_REV="$(git -C "${ROOT}" rev-parse HEAD 2>/dev/null || true)"
[ -n "${CURRENT_REV}" ] && { run bash -c "echo '${CURRENT_REV}' > '${REV_FILE}'"; } || warn "not a git checkout — rollback disabled"

restart_service() {
  if command -v systemctl >/dev/null && systemctl list-unit-files 2>/dev/null | grep -q '^claude-gateway'; then
    run sudo systemctl restart claude-gateway
  else
    warn "no systemd unit 'claude-gateway' — restart the server process yourself"
  fi
}

info "[1] pulling latest"
run git -C "${ROOT}" pull --ff-only || die "git pull failed (resolve manually)" 1

info "[2] reinstalling deps"
run "${PY}" -m pip install --quiet -e "${ROOT}[gateway]"

if [ "${CLAUDE_GATEWAY_DB:-memory}" = "postgres" ]; then
  info "[3] applying schema (create_all is additive/idempotent)"
  run "${PY}" -c "import asyncio; from gateway.shared.config import GatewaySettings; from gateway.shared.db.engine import Database; \
s=GatewaySettings(); db=Database(s.database_url); asyncio.run(db.create_all())"
fi

info "[4] restarting service"
restart_service

if [ "${DRY}" = "1" ]; then ok "dry-run complete — no changes made"; exit 0; fi

info "[5] health gate: ${HEALTH_URL}"
if health_probe "${HEALTH_URL}" 20 0.5; then
  ok "update complete — /health green"
else
  warn "health probe failed — rolling back"
  if [ -n "${CURRENT_REV}" ] && [ -f "${REV_FILE}" ]; then
    git -C "${ROOT}" checkout "$(cat "${REV_FILE}")" || die "rollback checkout failed" 5
    "${PY}" -m pip install --quiet -e "${ROOT}[gateway]"
    restart_service
    die "rolled back to $(cat "${REV_FILE}") — investigate the failed deploy" 5
  fi
  die "health failed and no rollback point — manual intervention required" 5
fi
