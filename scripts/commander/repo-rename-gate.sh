#!/usr/bin/env bash
set -euo pipefail

mkdir -p reports/repo-rename

if ! command -v gh >/dev/null 2>&1; then
  echo "NO-GO: GitHub CLI 'gh' is required for canonical repository verification."
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "NO-GO: git is required for repository verification."
  exit 1
fi

CANONICAL_REPO="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
CANONICAL_URL="$(gh repo view --json url --jq .url)"
HEAD_SHA="$(git rev-parse HEAD)"
BRANCH="$(git branch --show-current)"

{
  echo "=== REPO RENAME GATE ==="
  echo "canonical_repo=$CANONICAL_REPO"
  echo "canonical_url=$CANONICAL_URL"
  echo "branch=$BRANCH"
  echo "head_sha=$HEAD_SHA"
  echo "=== Local remotes ==="
  git remote -v
} | tee reports/repo-rename/canonical-repo.txt

if [[ "$CANONICAL_REPO" != "CurLexAI/swarms" ]]; then
  echo "NO-GO: canonical repository is '$CANONICAL_REPO', expected 'CurLexAI/swarms'."
  exit 1
fi

SEARCH_ROOTS=()
for path in README.md AGENTS.md agents .agents .github docs scripts package.json package-lock.json pnpm-lock.yaml yarn.lock; do
  if [[ -e "$path" ]]; then
    SEARCH_ROOTS+=("$path")
  fi
done

: > reports/repo-rename/stale-references.txt

if [[ ${#SEARCH_ROOTS[@]} -gt 0 ]]; then
  grep -RInE \
    "CurLexAI/LexPrim|LexBANK/BSM|MOTEB1989/LexPrim|AUTH_MISSING|api\.github\.com/repos/LexBANK|github\.com/LexBANK|api\.github\.com/repos/CurLexAI/LexPrim|github\.com/CurLexAI/LexPrim|api\.github\.com/repos/MOTEB1989/LexPrim|github\.com/MOTEB1989/LexPrim" \
    "${SEARCH_ROOTS[@]}" \
    --exclude-dir=.git \
    --exclude-dir=node_modules \
    --exclude-dir=.next \
    --exclude-dir=dist \
    --exclude-dir=build \
    > reports/repo-rename/stale-references.txt || true
fi

if [[ -s reports/repo-rename/stale-references.txt ]]; then
  echo "NO-GO: stale repository or invalid evidence references found."
  cat reports/repo-rename/stale-references.txt
  exit 1
fi

echo "=== Latest main runs ==="
gh run list \
  --repo "$CANONICAL_REPO" \
  --branch main \
  --limit 5 \
  --json databaseId,name,status,conclusion,headSha,createdAt,updatedAt,url \
  | tee reports/repo-rename/latest-main-runs.json

cat > reports/repo-rename/commander-report.md <<REPORT
=== COMMANDER REPORT ===
Mission: Repository rename readiness audit
Priority: P0
Owner: DevOps / Raptor
Status: PASS
Evidence:
- Canonical repo: $CANONICAL_REPO
- Canonical URL: $CANONICAL_URL
- Branch: $BRANCH
- Head SHA: $HEAD_SHA
- Latest main workflow runs: reports/repo-rename/latest-main-runs.json
- Stale references report: reports/repo-rename/stale-references.txt
Risks:
- A PASS from this script confirms checked repository content and recent workflow metadata only. External deploy hooks, third-party dashboards, and connector settings must still be verified in their own systems.
Decision: GO for repository-name references in checked paths; external hooks remain needs verification.
Next action: Run this gate after every repository rename and before go-live evidence is accepted.
REPORT

echo "PASS: no stale repository references found in checked paths."
echo "Report: reports/repo-rename/commander-report.md"
