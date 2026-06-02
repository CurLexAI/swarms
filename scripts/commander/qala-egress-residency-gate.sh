#!/usr/bin/env bash
# Qal'a Q8 — Egress Residency Gate
#
# Source-time check that repository-resident code does not call out to
# hosts outside the sovereign allowlist. Fail-closed: an empty
# allowlist, a scanner runtime failure, or an unparseable host all
# FAIL the gate.
#
# See .agents/policies/qala-egress-residency.md and
# docs/decisions/ADR-0003-qala-security-architecture.md §Q8.

set -euo pipefail

ROOT_DIR="${1:-.}"
cd "$ROOT_DIR"

status="PASS"
ok()   { echo "[OK]   $*"; }
warn() { echo "[WARN] $*"; }
fail() { echo "[FAIL] $*"; status="FAIL"; }
info() { echo "[INFO] $*"; }

info "Qal'a egress residency gate (Q8)"
info "repo=$(pwd)"

# Allowlist — must match `.agents/policies/qala-egress-residency.md`.
# Empty allowlist FAILs the gate.
ALLOWLIST=(
  "*.modal.run"
  "api.github.com"
  "github.com"
  "huggingface.co"
  "router.huggingface.co"
  "ollama"
  "llama-server"
  "qarar-security-gate"
  "login.microsoftonline.com"
)

if (( ${#ALLOWLIST[@]} == 0 )); then
  fail "ALLOWLIST_EMPTY: refusing to scan with no allowlist"
  echo "[RESULT] FAIL"
  exit 1
fi

SCAN_DIRS=(.agents src scripts sama_ingestion_swarm)
EXISTING_SCAN_DIRS=()
for d in "${SCAN_DIRS[@]}"; do
  [[ -d "$d" ]] && EXISTING_SCAN_DIRS+=("$d")
done

if (( ${#EXISTING_SCAN_DIRS[@]} == 0 )); then
  warn "no scannable directories present"
  echo "[RESULT] PASS"
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
  fail "PYTHON3_MISSING: cannot run egress scanner"
  echo "[RESULT] FAIL"
  exit 1
fi

# Python scanner. Exit codes:
#   0  -> clean (no unapproved hosts) — gate PASSes
#   10 -> at least one unapproved host found — gate FAILs
#   2+ -> scanner runtime failure — gate FAILs (fail-closed)
set +e
scan_output="$(python3 - "${EXISTING_SCAN_DIRS[@]}" <<'PY'
import os, re, sys
from fnmatch import fnmatch

ALLOWLIST = (
    "*.modal.run",
    "api.github.com",
    "github.com",
    "huggingface.co",
    "router.huggingface.co",
    "ollama",
    "llama-server",
    "qarar-security-gate",
    "login.microsoftonline.com",
)

# RFC 2606 / RFC 6761 reserved special-use names. These cannot route in
# production by definition, so a literal occurrence in source code is
# documentation/test data, not live egress.
RESERVED_DOMAINS = (
    "example", "*.example",
    "example.com", "*.example.com",
    "example.net", "*.example.net",
    "example.org", "*.example.org",
    "invalid", "*.invalid",
    "localhost", "*.localhost",
    "test", "*.test",
)

# RFC 5737 documentation IP blocks — never globally routable.
RESERVED_IP_PREFIXES = ("192.0.2.", "198.51.100.", "203.0.113.")

# Pull bare URLs out of source. We accept http(s) only. The optional
# `userinfo@` segment is consumed so it is not mistaken for the host.
URL_RE = re.compile(
    r"https?://(?:[^@/\s'\"`)]*@)?([A-Za-z0-9._-]+)(?:[:/][^\s'\"`)]*)?"
)
# Also flag IP literals explicitly — static IPs are forbidden, except
# for the reserved documentation ranges above.
IP_RE = re.compile(
    r"https?://(?:[^@/\s'\"`)]*@)?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
)

# Files that may reference example URLs without making network calls.
SKIP_DIRS = {"node_modules", ".git", ".next", "dist", "build", "__pycache__", ".venv", "tests"}
# Source-only extensions; docs/policies are not scanned.
EXTS = (".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".sh")

def is_allowed(host: str) -> bool:
    for pat in ALLOWLIST:
        if fnmatch(host, pat):
            return True
    for pat in RESERVED_DOMAINS:
        if fnmatch(host, pat):
            return True
    return False


def is_reserved_ip(ip: str) -> bool:
    for prefix in RESERVED_IP_PREFIXES:
        if ip.startswith(prefix):
            return True
    return False

hits: list[tuple[str, str]] = []  # (host, source_path)
ip_hits: list[tuple[str, str]] = []
scanner_error = False

for root_arg in sys.argv[1:]:
    for root, dirs, files in os.walk(root_arg, followlinks=False):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            if not fn.endswith(EXTS):
                continue
            path = os.path.join(root, fn)
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except OSError as e:
                sys.stderr.write(f"scan_error: {path}: {e}\n")
                scanner_error = True
                continue

            for m in IP_RE.finditer(content):
                ip = m.group(1)
                if not is_reserved_ip(ip):
                    ip_hits.append((ip, path))

            for m in URL_RE.finditer(content):
                host = m.group(1).lower()
                # Skip if the captured group is an IP literal — already
                # handled by IP_RE above.
                if re.fullmatch(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", host):
                    continue
                if not is_allowed(host):
                    hits.append((host, path))

if scanner_error:
    sys.exit(2)

# Report
unique_unapproved = sorted({h for h, _ in hits})
unique_ips = sorted({h for h, _ in ip_hits})

print(f"EGRESS_HOSTS_SCANNED: {len(hits) + len(ip_hits)}")
print(f"ALLOWLIST: {','.join(ALLOWLIST)}")
print(f"UNAPPROVED_HOSTS: {','.join(unique_unapproved) if unique_unapproved else 'NONE'}")
print(f"IP_LITERALS: {','.join(unique_ips) if unique_ips else 'NONE'}")

for host, path in hits:
    print(f"  unapproved: {host} -> {path}")
for ip, path in ip_hits:
    print(f"  ip_literal: {ip} -> {path}")

sys.exit(10 if (hits or ip_hits) else 0)
PY
)"
py_rc=$?
set -e

printf '%s\n' "$scan_output"

case "$py_rc" in
  0)
    ok "no unapproved egress destinations detected"
    ;;
  10)
    fail "UNAPPROVED_EGRESS: hosts outside the Q8 allowlist were found"
    ;;
  *)
    fail "SCANNER_ERROR: egress scanner exited rc=$py_rc"
    ;;
esac

if [[ "$status" == "PASS" ]]; then
  echo "[RESULT] PASS"
  exit 0
fi
echo "[RESULT] FAIL"
exit 1
