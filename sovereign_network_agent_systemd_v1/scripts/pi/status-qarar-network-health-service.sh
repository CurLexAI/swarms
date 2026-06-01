#!/usr/bin/env bash
set -euo pipefail
SERVICE_NAME="qarar-network-health.service"
if [[ "${EUID}" -ne 0 ]]; then
  exec sudo -E bash "$0" "$@"
fi
systemctl --no-pager --full status "$SERVICE_NAME" || true
journalctl -u "$SERVICE_NAME" -n 80 --no-pager || true
if [[ -f /var/log/qarar-network-agent/network-health.jsonl ]]; then
  echo "--- audit tail ---"
  tail -n 20 /var/log/qarar-network-agent/network-health.jsonl || true
fi
