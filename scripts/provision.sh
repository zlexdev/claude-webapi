#!/usr/bin/env bash
# Onboard a claude.ai account and mint an API key in one call.
#
# Cookies are read from env or stdin — NEVER argv (visible in ps/history). To pass
# Cloudflare you need the FULL cookie jar (sessionKey + cf_clearance + __cf_bm +
# _cfuvid), copied from a browser that passes the challenge on this IP:
#
#   CLAUDE_COOKIES='sessionKey=...; cf_clearance=...; __cf_bm=...; _cfuvid=...' \
#     scripts/provision.sh --org <uuid> --name cli
#   # or paste the cookie string on stdin:
#   pbpaste | scripts/provision.sh --org <uuid>
#   # bare sessionKey still works (but org-scoped calls will 403 without cf_clearance):
#   CLAUDE_SESSION_KEY=sk-ant-sid02-... scripts/provision.sh
#
# Requires CLAUDE_GATEWAY_ADMIN_TOKEN (from .env) and a running gateway. The gateway
# must run with CLAUDE_AI_USER_AGENT matching the browser the cookies came from.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
load_env

ORG=""; NAME="provisioned"
while [ $# -gt 0 ]; do
  case "$1" in
    --org)  ORG="$2"; shift 2 ;;
    --name) NAME="$2"; shift 2 ;;
    *) shift ;;
  esac
done

: "${CLAUDE_GATEWAY_ADMIN_TOKEN:?CLAUDE_GATEWAY_ADMIN_TOKEN must be set (see .env)}"
RAW="${CLAUDE_COOKIES:-}"
[ -z "${RAW}" ] && [ -n "${CLAUDE_SESSION_KEY:-}" ] && RAW="sessionKey=${CLAUDE_SESSION_KEY}"
if [ -z "${RAW}" ]; then
  [ -t 0 ] && info "paste the cookie string (or bare sessionKey), then Ctrl-D:"
  RAW="$(cat)"
fi
[ -n "${RAW}" ] || die "no cookies provided (env CLAUDE_COOKIES / CLAUDE_SESSION_KEY / stdin)"

HOST="${CLAUDE_GATEWAY_HOST:-127.0.0.1}"; [ "${HOST}" = "0.0.0.0" ] && HOST="127.0.0.1"
URL="http://${HOST}:${CLAUDE_GATEWAY_PORT:-8081}/system/keys/generate"

BODY="$(RAW="${RAW}" ORG="${ORG}" NAME="${NAME}" "${PY}" - <<'PYEOF'
import json, os
raw = os.environ["RAW"].strip()
cookies: dict[str, str] = {}
if "=" in raw:
    for pair in raw.split(";"):
        pair = pair.strip()
        if "=" in pair:
            k, _, v = pair.partition("=")
            cookies[k.strip()] = v.strip()
else:
    cookies["sessionKey"] = raw  # bare token
body = {"cookies": cookies, "name": os.environ["NAME"]}
if os.environ.get("ORG"):
    body["org_uuid"] = os.environ["ORG"]
print(json.dumps(body))
PYEOF
)"

info "provisioning account + key at ${URL} (cookies redacted)"
RESP="$(curl -fsS -X POST "${URL}" \
  -H "X-Admin-Token: ${CLAUDE_GATEWAY_ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  --data-binary "${BODY}")" || die "request failed — is the gateway running and the admin token correct?"

KEY="$(printf '%s' "${RESP}" | "${PY}" -c 'import sys,json; print(json.load(sys.stdin).get("key",""))' 2>/dev/null || true)"
[ -n "${KEY}" ] || die "no key in response: ${RESP}"
ok "API key (shown once): ${KEY}"
