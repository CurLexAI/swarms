#!/usr/bin/env bash
set -euo pipefail

REPO_URL_HOST="${SWARMS_REPO_HOST:-github.com}"
REPO_URL_PATH="${SWARMS_REPO_PATH:-CurLexAI/swarms.git}"
REPO_URL="https://${REPO_URL_HOST}/${REPO_URL_PATH}"
WORK_ROOT="${WORK_ROOT:-/tmp/swarms-extraction}"
CLONE_DIR="${WORK_ROOT}/repo"
NOW_UTC="$(date -u +%Y%m%d-%H%M%S)"
REPORT_PATH="docs/operations/reports/swarms-extraction-${NOW_UTC}.md"

mkdir -p "${WORK_ROOT}" "docs/operations/reports"

if ! gh auth status --hostname github.com >/dev/null 2>&1; then
  cat > "${REPORT_PATH}" <<REPORT
Execution Verdict:
- Status: BLOCKED
- Scope: Verify swarms extraction workflow script prerequisites and repository shape.
- Canonical Path: scripts/verify_swarms_extraction.sh
- Files Touched: ${REPORT_PATH}
- Blockers: AUTH_MISSING (gh auth status failed for github.com)
- Hot Surface Risk: LOW
- What Was Actually Changed: Generated blocker report only.
- What Was Actually Verified: none
- What Remains Unverified: GitHub clone and extraction checks.
- Next Valid Action: Authenticate with GitHub CLI and rerun this script.
REPORT
  printf 'BLOCKER AUTH_MISSING: GitHub CLI authentication is required. Report: %s\n' "${REPORT_PATH}" >&2
  exit 2
fi

rm -rf "${CLONE_DIR}"
git clone --depth=1 --quiet "${REPO_URL}" "${CLONE_DIR}"

md_count="$(find "${CLONE_DIR}" -type f \( -name '*.md' -o -name '*.markdown' \) | wc -l | tr -d ' ')"
py_count="$(find "${CLONE_DIR}" -type f \( -name '*.py' -o -name '*.pyi' \) | wc -l | tr -d ' ')"

find "${CLONE_DIR}" -type f \( -name '*.md' -o -name '*.py' \) -print0 \
  | xargs -0 sha256sum > "${WORK_ROOT}/content.sha256"

cat > "${REPORT_PATH}" <<REPORT
Execution Verdict:
- Status: CHANGED_BUT_NOT_VERIFIED
- Scope: Verify swarms extraction workflow script prerequisites and repository shape.
- Canonical Path: scripts/verify_swarms_extraction.sh
- Files Touched: ${REPORT_PATH}
- Blockers: none
- Hot Surface Risk: LOW
- What Was Actually Changed: Created local shallow clone and generated file inventory hash list.
- What Was Actually Verified: gh auth status succeeded; clone command executed; markdown_count=${md_count}; python_count=${py_count}.
- What Remains Unverified: Runtime semantics of downstream extraction consumers.
- Next Valid Action: Compare generated hash list and counts against expected extraction baseline.
REPORT

printf 'Report saved: %s\n' "${REPORT_PATH}"
