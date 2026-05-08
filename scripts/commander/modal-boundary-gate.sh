#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-.}"
cd "$ROOT_DIR"

status="PASS"
ok()   { echo "[OK]   $*"; }
warn() { echo "[WARN] $*"; }
fail() { echo "[FAIL] $*"; status="FAIL"; }
info() { echo "[INFO] $*"; }

info "Modal boundary gate"
info "repo=$(pwd)"

# ── 1. No direct Modal endpoint URLs in client/public/server-rendered paths ──
PUBLIC_DIRS=(src public app pages components)
EXISTING_DIRS=()
for d in "${PUBLIC_DIRS[@]}"; do
  [[ -d "$d" ]] && EXISTING_DIRS+=("$d")
done

if (( ${#EXISTING_DIRS[@]} > 0 )); then
  if grep -RIn \
       --exclude-dir=.git --exclude-dir=node_modules \
       --exclude-dir=.next --exclude-dir=dist --exclude-dir=build \
       '\.modal\.run' "${EXISTING_DIRS[@]}" 2>/dev/null; then
    fail "MODAL_URL_LEAK: direct *.modal.run reference in public/client paths"
  else
    ok "no *.modal.run reference in $(IFS=, ; echo "${EXISTING_DIRS[*]}")"
  fi
else
  warn "no public/client directories to scan (skipped)"
fi

# ── 2. Modal SDK must not be imported from client/public surfaces ────────────
# Covers four import shapes × three string-literal forms (', ", `), and
# allows whitespace -- including newlines -- between any two tokens, so
# valid JS/TS formatting like
#     import (
#       "modal"
#     )
# or `from\n  'modal'` is also flagged.
#
# Implemented in python3 rather than `grep -P` because PCRE support is
# GNU-grep-specific. On BSD/macOS grep there is no -P flag, and the
# previous form silently false-passed: the option error was swallowed by
# 2>/dev/null and the if/else fell into the "ok" branch. The python
# scanner uses an explicit tri-state exit code so a runtime failure is
# FAIL, never silently OK:
#   0  -> at least one offending file (FAIL)
#   1  -> clean (OK)
#   ≥2 -> scanner itself failed (FAIL, fail-closed)
if (( ${#EXISTING_DIRS[@]} > 0 )); then
  if ! command -v python3 >/dev/null 2>&1; then
    fail "PYTHON3_MISSING: cannot run Modal SDK import scan"
  else
    # Temporarily disable errexit: rc=1 means "no matches" and is normal.
    # We inspect rc explicitly below.
    set +e
    scan_output="$(python3 - "${EXISTING_DIRS[@]}" <<'PY'
import os, re, sys

pattern = re.compile(
    r"(from|require\s*\(|import)\s*\(?\s*['\"`]modal['\"`]",
    re.MULTILINE | re.DOTALL,
)
exts = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
skip_dirs = {"node_modules", ".next", "dist", "build", ".git"}

# Follow symlinked directories (GNU `grep -R` does too). Track real paths
# of visited dirs so a cycle like `src/vendor -> ..` cannot loop forever.
hits = []
visited = set()
for root_arg in sys.argv[1:]:
    for root, dirs, files in os.walk(root_arg, followlinks=True):
        real = os.path.realpath(root)
        if real in visited:
            dirs[:] = []
            continue
        visited.add(real)
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fn in files:
            if not fn.endswith(exts):
                continue
            path = os.path.join(root, fn)
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    if pattern.search(f.read()):
                        hits.append(path)
            except OSError as e:
                # An unreadable file is a scanner failure, not a silent pass.
                sys.stderr.write(f"scan_error: {path}: {e}\n")
                sys.exit(2)

for h in hits:
    print(h)
sys.exit(0 if hits else 1)
PY
    )"
    py_rc=$?
    set -e
    case "$py_rc" in
      0)
        printf '%s\n' "$scan_output"
        fail "MODAL_SDK_IMPORT_IN_CLIENT: 'modal' SDK imported from public/client paths"
        ;;
      1)
        ok "no Modal SDK import found in client surfaces"
        ;;
      *)
        fail "MODAL_SDK_SCAN_FAILED: python scanner exited rc=$py_rc"
        ;;
    esac
  fi
fi

# ── 3. Server-side relay must exist before agents are wired ──────────────────
if [[ -f .agents/pr_review.py ]]; then
  ok "server-side relay present (.agents/pr_review.py)"
else
  fail "RELAY_MISSING: .agents/pr_review.py not found"
fi

# ── 4. Router/validators packages are reachable ──────────────────────────────
for pkg in .agents/router/__init__.py .agents/validators/__init__.py; do
  if [[ -f "$pkg" ]]; then
    ok "package init present: $pkg"
  else
    warn "package init missing: $pkg"
  fi
done

# ── 5. Secrets boundary: presence reported, never echoed ─────────────────────
for v in BAYYINAH_ENDPOINT MIHWAR_ENDPOINT AGENT_API_TOKEN; do
  if [[ -n "${!v:-}" ]]; then
    ok "$v=SET"
  else
    warn "SECRET_MISSING: $v (expected outside CI/runtime)"
  fi
done

# ── 6. Workflow uses `secrets.*` indirection (never hardcoded URLs) ──────────
WF=.github/workflows/agent-review.yml
if [[ -f "$WF" ]]; then
  if grep -E 'https?://[^[:space:]]*\.modal\.run' "$WF" >/dev/null 2>&1; then
    fail "WORKFLOW_HARDCODED_MODAL_URL: $WF"
  else
    ok "workflow $WF has no hardcoded modal URL"
  fi
else
  warn "workflow not found: $WF"
fi

# ── 7. ADR-0001 boundary regression gate ────────────────────────────────────
ADR_GATE=scripts/commander/adr-0001-boundary-gate.sh
if [[ -f "$ADR_GATE" ]]; then
  if bash "$ADR_GATE" "$ROOT_DIR"; then
    ok "ADR-0001 boundary gate passed"
  else
    fail "ADR_0001_BOUNDARY_REGRESSION"
  fi
else
  warn "boundary gate not found: $ADR_GATE"
fi

if [[ "$status" == "PASS" ]]; then
  echo "[RESULT] PASS"
  exit 0
else
  echo "[RESULT] FAIL"
  exit 1
fi
