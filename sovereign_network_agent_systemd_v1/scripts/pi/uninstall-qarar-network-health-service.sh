#!/usr/bin/env bash
set -euo pipefail
SERVICE_NAME="qarar-network-health.service"
if [[ "${EUID}" -ne 0 ]]; then
  exec sudo -E bash "$0" "$@"
fi
systemctl stop "$SERVICE_NAME" >/dev/null 2>&1 || true
systemctl disable "$SERVICE_NAME" >/dev/null 2>&1 || true
rm -f "/etc/systemd/system/$SERVICE_NAME"
systemctl daemon-reload
# Keep /var/log/qarar-network-agent and /var/lib/qarar-network-agent for audit preservation.
echo "OK: removed $SERVICE_NAME. Audit logs preserved."
