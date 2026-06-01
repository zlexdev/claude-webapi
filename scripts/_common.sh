#!/usr/bin/env bash
# Shared helpers for the gateway ops scripts. Source this from each script.
#
# Flags parsed by parse_flags (set before sourcing-time work):
#   --dry-run          DRY=1   — run() prints instead of executing
#   --non-interactive  NONINT=1 — prompt_cached never prompts, uses default
#   --reset            RESET=1 — prompt_cached ignores the cache
set -euo pipefail

C_BLUE='\033[0;34m'; C_GREEN='\033[0;32m'; C_YELLOW='\033[0;33m'; C_RED='\033[0;31m'; C_OFF='\033[0m'
info()  { printf "${C_BLUE}==>${C_OFF} %s\n" "$*"; }
ok()    { printf "${C_GREEN}OK ${C_OFF} %s\n" "$*"; }
warn()  { printf "${C_YELLOW}!! ${C_OFF} %s\n" "$*"; }
die()   { printf "${C_RED}ERR${C_OFF} %s\n" "$*" >&2; exit "${2:-1}"; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${ROOT}/.venv"
PY="${VENV}/bin/python"
CACHE="${ROOT}/scripts/.gateway.cache"

DRY="${DRY:-0}"; NONINT="${NONINT:-0}"; RESET="${RESET:-0}"

parse_flags() {
  for arg in "$@"; do
    case "$arg" in
      --dry-run)         DRY=1 ;;
      --non-interactive) NONINT=1 ;;
      --reset)           RESET=1 ;;
      *) ;;
    esac
  done
}

# run CMD...  — execute, or print when DRY=1. Never use for read-only commands.
run() {
  if [ "${DRY}" = "1" ]; then
    printf "${C_YELLOW}dry${C_OFF} %s\n" "$*"
  else
    "$@"
  fi
}

load_env() {
  [ -f "${ROOT}/.env" ] || die ".env not found — copy .env.example to .env and edit it"
  set -a; # shellcheck disable=SC1091
  . "${ROOT}/.env"; set +a
}

# prompt_cached VAR "Question" "default" — read a value, remembering it in CACHE.
# Honors NONINT (never prompts) and RESET (ignores cached value). chmod 600.
prompt_cached() {
  local var="$1" question="$2" default="${3:-}" cached=""
  [ -f "${CACHE}" ] && cached="$(grep -E "^${var}=" "${CACHE}" 2>/dev/null | head -n1 | cut -d= -f2- || true)"
  [ "${RESET}" = "1" ] && cached=""
  local fallback="${cached:-$default}"
  local value="${fallback}"
  if [ "${NONINT}" != "1" ] && [ -t 0 ]; then
    read -r -p "${question} [${fallback}]: " value || true
    value="${value:-$fallback}"
  fi
  touch "${CACHE}"; chmod 600 "${CACHE}"
  if grep -qE "^${var}=" "${CACHE}" 2>/dev/null; then
    sed -i.bak "s|^${var}=.*|${var}=${value}|" "${CACHE}" && rm -f "${CACHE}.bak"
  else
    printf "%s=%s\n" "${var}" "${value}" >> "${CACHE}"
  fi
  printf '%s' "${value}"
}

# health_probe URL [retries] [sleep_s] — poll until HTTP 200, else non-zero.
health_probe() {
  local url="$1" retries="${2:-20}" nap="${3:-0.5}" code=""
  for _ in $(seq 1 "${retries}"); do
    code="$(curl -fsS -o /dev/null -w '%{http_code}' "${url}" 2>/dev/null || true)"
    [ "${code}" = "200" ] && return 0
    sleep "${nap}"
  done
  return 1
}
