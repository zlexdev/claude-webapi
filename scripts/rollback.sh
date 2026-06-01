#!/usr/bin/env bash
# Back out the last update.sh: checkout the recorded revision + reinstall. Schema is
# forward-only/additive, so no DB downgrade is performed (restore from backup if needed).
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
load_env
REV_FILE="${ROOT}/.last_deploy_rev"
[ -f "${REV_FILE}" ] || die "no .last_deploy_rev — nothing to roll back to"
REV="$(cat "${REV_FILE}")"
info "rolling back to ${REV}"
git -C "${ROOT}" checkout "${REV}" || die "checkout failed"
"${PY}" -m pip install --quiet -e "${ROOT}[gateway]"
ok "rolled back — restart the service. (DB schema is additive; restore a backup if a column must go.)"
