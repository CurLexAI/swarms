#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_PATH="${QARAR_LOG_PATH:-$ROOT/logs/network-health.jsonl}"
mkdir -p "$(dirname "$LOG_PATH")"
QARAR_NETWORK_DRY_RUN=true \
QARAR_ENABLE_ROUTER_REBOOT=false \
QARAR_LOG_PATH="$LOG_PATH" \
python3 -u "$ROOT/network_health_guard.py" --once

tail -n 3 "$LOG_PATH" || true
