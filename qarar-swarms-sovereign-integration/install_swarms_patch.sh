#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${1:-.}"
INSTALL_PYTHON_DEPS="${2:-}"
REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"
OVERLAY_ROOT="$SCRIPT_DIR/overlay"
REPORT_PATH="$REPO_ROOT/docs/operations/swarms-qarar-integration-report.md"
SUMMARY_PATH="$REPO_ROOT/swarms-qarar-integration-summary.json"
CREATED_LIST="$(mktemp)"
SKIPPED_LIST="$(mktemp)"
CONFLICT_LIST="$(mktemp)"
TEST_LIST="$(mktemp)"

cleanup() {
  rm -f "$CREATED_LIST" "$SKIPPED_LIST" "$CONFLICT_LIST" "$TEST_LIST"
}
trap cleanup EXIT

fail() {
  echo "[FAIL] $1" >&2
  exit 1
}

info() {
  echo "[INFO] $1"
}

record_created() { printf '%s\n' "$1" >> "$CREATED_LIST"; }
record_skipped() { printf '%s\n' "$1" >> "$SKIPPED_LIST"; }
record_conflict() { printf '%s\n' "$1" >> "$CONFLICT_LIST"; }
record_test() { printf '%s\n' "$1" >> "$TEST_LIST"; }

is_repo_root() {
  [ -f "$REPO_ROOT/package.json" ] || [ -d "$REPO_ROOT/.git" ] || [ -d "$REPO_ROOT/src" ] || [ -f "$REPO_ROOT/AGENTS.md" ]
}

copy_additive_file() {
  local src="$1"
  local dst="$2"
  local rel="${dst#$REPO_ROOT/}"
  mkdir -p "$(dirname "$dst")"

  if [ ! -e "$dst" ]; then
    cp "$src" "$dst"
    record_created "$rel"
    return 0
  fi

  if cmp -s "$src" "$dst"; then
    record_skipped "$rel identical"
    return 0
  fi

  local candidate="$dst.candidate"
  cp "$src" "$candidate"
  record_conflict "$rel existing differs; wrote ${rel}.candidate"
}

copy_tree_additive() {
  local source_dir="$1"
  local target_dir="$2"
  while IFS= read -r -d '' file; do
    local rel="${file#$source_dir/}"
    copy_additive_file "$file" "$target_dir/$rel"
  done < <(find "$source_dir" -type f -print0 | sort -z)
}

json_lines() {
  python3 -c 'import json, pathlib, sys; print(json.dumps(pathlib.Path(sys.argv[1]).read_text().splitlines(), ensure_ascii=False))' "$1" 2>/dev/null || echo '[]'
}

run_node_tests() {
  local target="$REPO_ROOT/qarar/packages/bayyinah"
  if ! command -v node >/dev/null 2>&1; then
    record_test "node missing; skipped Bayyinah Swarms tests"
    return 0
  fi

  if [ ! -f "$target/package.json" ]; then
    record_test "Bayyinah package.json missing; skipped node tests"
    return 0
  fi

  info "running Bayyinah Swarms tests"
  (cd "$target" && node --experimental-strip-types --test "./tests/swarms-*.test.ts")
  record_test "Bayyinah Swarms tests passed"
}

run_python_tests() {
  if ! command -v python3 >/dev/null 2>&1; then
    record_test "python3 missing; skipped Python adapter tests"
    return 0
  fi

  info "running Python Swarms adapter tests"
  PYTHONPATH="$REPO_ROOT/integrations/python" python3 -m unittest "$REPO_ROOT/integrations/python/test_qarar_swarms_adapter.py"
  record_test "Python Swarms adapter tests passed"
}

install_python_deps() {
  if [ "$INSTALL_PYTHON_DEPS" != "--install-python-deps" ]; then
    info "python dependency installation skipped; requirements.swarms.txt copied"
    return 0
  fi

  if ! command -v python3 >/dev/null 2>&1; then
    fail "python3 is required for --install-python-deps"
  fi

  info "installing pinned Python Swarms dependencies"
  python3 -m pip install -r "$REPO_ROOT/requirements.swarms.txt"
}

write_report() {
  mkdir -p "$(dirname "$REPORT_PATH")"
  local timestamp status
  timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  status="ready_for_swarms_integration_pr"
  if [ -s "$CONFLICT_LIST" ]; then
    status="conflicts_need_review"
  fi

  {
    echo "# Swarms x Qarar Integration Report"
    echo
    echo "- timestamp_utc: $timestamp"
    echo "- status: $status"
    echo "- target: qarar/packages/bayyinah + integrations/python/qarar_swarms"
    echo "- mode: safe additive overlay"
    echo
    echo "## Created"
    if [ -s "$CREATED_LIST" ]; then sed 's/^/- /' "$CREATED_LIST"; else echo "- none"; fi
    echo
    echo "## Skipped"
    if [ -s "$SKIPPED_LIST" ]; then sed 's/^/- /' "$SKIPPED_LIST"; else echo "- none"; fi
    echo
    echo "## Conflicts"
    if [ -s "$CONFLICT_LIST" ]; then sed 's/^/- /' "$CONFLICT_LIST"; else echo "- none"; fi
    echo
    echo "## Tests"
    if [ -s "$TEST_LIST" ]; then sed 's/^/- /' "$TEST_LIST"; else echo "- none"; fi
    echo
    echo "## Safety"
    echo "- no destructive database operation performed"
    echo "- no secret written"
    echo "- no security middleware disabled"
    echo "- existing differing files were not overwritten"
  } > "$REPORT_PATH"

  local created_json skipped_json conflicts_json tests_json
  created_json="$(json_lines "$CREATED_LIST")"
  skipped_json="$(json_lines "$SKIPPED_LIST")"
  conflicts_json="$(json_lines "$CONFLICT_LIST")"
  tests_json="$(json_lines "$TEST_LIST")"

  cat > "$SUMMARY_PATH" <<JSON
{
  "status": "$status",
  "target": "qarar/packages/bayyinah + integrations/python/qarar_swarms",
  "report": "docs/operations/swarms-qarar-integration-report.md",
  "created": $created_json,
  "skipped": $skipped_json,
  "conflicts": $conflicts_json,
  "tests": $tests_json
}
JSON

  info "report written: ${REPORT_PATH#$REPO_ROOT/}"
  info "summary written: ${SUMMARY_PATH#$REPO_ROOT/}"
  echo "status=$status"
}

main() {
  [ -d "$OVERLAY_ROOT" ] || fail "overlay directory missing: $OVERLAY_ROOT"
  is_repo_root || fail "target does not look like a repository root: $REPO_ROOT"

  info "repo root: $REPO_ROOT"
  copy_tree_additive "$OVERLAY_ROOT" "$REPO_ROOT"
  install_python_deps
  run_node_tests
  run_python_tests
  write_report
}

main "$@"
