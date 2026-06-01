#!/usr/bin/env bash
# End-to-end smoke: boot an ephemeral in-memory gateway, provision a real account
# from the FULL cookie jar, mint a key, then exercise every surface.
#
#   CLAUDE_SMOKE_COOKIES='sessionKey=...; cf_clearance=...; __cf_bm=...; _cfuvid=...' \
#   CLAUDE_SMOKE_ORG_UUID=<uuid>  scripts/smoke.sh
#   # bare sessionKey also accepted (live calls will 403 without cf_clearance):
#   CLAUDE_SMOKE_SESSION_KEY=sk-ant-sid02-...  scripts/smoke.sh
#
# Cloudflare needs cf_clearance + a matching UA — set CLAUDE_SMOKE_USER_AGENT to the
# browser the cookies came from (default = the SDK default, Chrome 148).
#
# Exit 0 iff every gateway-WIRING check passes; upstream failures (claude.ai 403
# cf-challenge, 429 rate-limit, 5xx) are reported but NOT fatal.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

RAW="${CLAUDE_SMOKE_COOKIES:-}"
[ -z "${RAW}" ] && [ -n "${CLAUDE_SMOKE_SESSION_KEY:-}" ] && RAW="sessionKey=${CLAUDE_SMOKE_SESSION_KEY}"
[ -n "${RAW}" ] || die "set CLAUDE_SMOKE_COOKIES (full jar) or CLAUDE_SMOKE_SESSION_KEY"
[ -x "${PY}" ] || die "venv missing — run scripts/install.sh first"

PORT="${CLAUDE_SMOKE_PORT:-8099}"
BASE="http://127.0.0.1:${PORT}"
ADMIN_TOKEN="$("${PY}" -c 'import secrets; print(secrets.token_urlsafe(24))')"
TMP="$(mktemp -d)"; SRV_LOG="${TMP}/server.log"
WIRING_FAILS=0

cleanup() { [ -n "${SRV_PID:-}" ] && kill "${SRV_PID}" 2>/dev/null || true; rm -rf "${TMP}"; }
trap cleanup EXIT

info "booting ephemeral gateway on :${PORT} (memory DB)"
CLAUDE_GATEWAY_DB=memory \
CLAUDE_GATEWAY_ADMIN_TOKEN="${ADMIN_TOKEN}" \
CLAUDE_GATEWAY_HOST=127.0.0.1 \
CLAUDE_GATEWAY_PORT="${PORT}" \
${CLAUDE_SMOKE_USER_AGENT:+CLAUDE_AI_USER_AGENT="${CLAUDE_SMOKE_USER_AGENT}"} \
  "${PY}" -m gateway >"${SRV_LOG}" 2>&1 &
SRV_PID=$!

health_probe "${BASE}/health" 40 0.5 || { warn "server did not come up; log:"; cat "${SRV_LOG}"; die "boot failed"; }
ok "gateway up (pid ${SRV_PID})"

info "provisioning account + key (cookies redacted)"
BODY="$(RAW="${RAW}" ORG="${CLAUDE_SMOKE_ORG_UUID:-}" "${PY}" - <<'PYEOF'
import json, os
raw = os.environ["RAW"].strip()
ck = {}
if "=" in raw:
    for p in raw.split(";"):
        p = p.strip()
        if "=" in p:
            k, _, v = p.partition("="); ck[k.strip()] = v.strip()
else:
    ck["sessionKey"] = raw
b = {"cookies": ck, "name": "smoke"}
if os.environ.get("ORG"): b["org_uuid"] = os.environ["ORG"]
print(json.dumps(b))
PYEOF
)"
PROV="$(curl -fsS -X POST "${BASE}/system/keys/generate" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" -H "Content-Type: application/json" \
  --data-binary "${BODY}" 2>"${TMP}/prov.err")" \
  || { warn "provision failed:"; cat "${TMP}/prov.err"; die "cannot provision account"; }
API_KEY="$(printf '%s' "${PROV}" | "${PY}" -c 'import sys,json; print(json.load(sys.stdin).get("key",""))')"
[ -n "${API_KEY}" ] || die "no key minted: ${PROV}"
ok "minted API key (redacted)"

# check NAME METHOD PATH AUTH [json-body] [expect-substr]
check() {
  local name="$1" method="$2" path="$3" auth="$4" data="${5:-}" want="${6:-}"
  local body_file="${TMP}/${name//\//_}.out" code hdr=()
  [ "${auth}" = "key" ] && hdr=(-H "Authorization: Bearer ${API_KEY}")
  if [ -n "${data}" ]; then
    code="$(curl -sS -o "${body_file}" -w '%{http_code}' -X "${method}" "${BASE}${path}" \
      "${hdr[@]}" -H "Content-Type: application/json" --data-binary "${data}" 2>/dev/null || echo 000)"
  else
    code="$(curl -sS -o "${body_file}" -w '%{http_code}' -X "${method}" "${BASE}${path}" "${hdr[@]}" 2>/dev/null || echo 000)"
  fi
  if [ "${code}" = "200" ] && { [ -z "${want}" ] || grep -q "${want}" "${body_file}"; }; then
    ok "$(printf '%-26s PASS  http=%s kind=wiring' "${name}" "${code}")"
    return
  fi
  # claude.ai-side conditions are not gateway defects.
  if [ "${code}" = "429" ] || { [ "${code}" -ge 500 ] 2>/dev/null; } \
     || grep -qiE 'cloudflare|just a moment|cf-mitigated|challenge|rate.?limit|forbidden by anthropic' "${body_file}"; then
    warn "$(printf '%-26s FAIL  http=%s kind=upstream (claude.ai-side, not gateway)' "${name}" "${code}")"
  else
    warn "$(printf '%-26s FAIL  http=%s kind=wiring' "${name}" "${code}")"
    WIRING_FAILS=$((WIRING_FAILS + 1))
  fi
  head -c 240 "${body_file}" | sed 's/^/      /'; printf '\n'
}

info "running surface checks"
check "health"               GET  "/health"               none
check "v1/models"            GET  "/v1/models"            key
check "v1/chats/list"        GET  "/v1/chats/list?limit=3" key
check "v1/prompt"            POST "/v1/prompt"            key  '{"text":"ping"}'
check "v1/chat-nonstream"    POST "/v1/chat/completions"  key  '{"model":"claude-sonnet-4-6","messages":[{"role":"user","content":"say hi"}]}'
check "v1/chat-stream"       POST "/v1/chat/completions"  key  '{"model":"claude-sonnet-4-6","stream":true,"messages":[{"role":"user","content":"say hi"}]}'  '[DONE]'

echo
if [ "${WIRING_FAILS}" -eq 0 ]; then
  ok "SMOKE PASSED — all gateway-wiring checks green"
  exit 0
fi
die "SMOKE FAILED — ${WIRING_FAILS} gateway-wiring check(s) failed" 1
