#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="qarar-network-health.service"
INSTALL_ROOT="${QARAR_INSTALL_ROOT:-/opt/sovereign-network-agent}"
SERVICE_USER="${QARAR_SERVICE_USER:-qarar-netguard}"
SERVICE_GROUP="${QARAR_SERVICE_GROUP:-qarar-netguard}"
LOG_DIR="${QARAR_LOG_DIR:-/var/log/qarar-network-agent}"
STATE_DIR="${QARAR_STATE_DIR:-/var/lib/qarar-network-agent}"
STRICT_REQUIREMENTS="${QARAR_REQUIREMENTS_STRICT:-false}"
START_SERVICE="${QARAR_START_SERVICE:-true}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [[ "${EUID}" -ne 0 ]]; then
  exec sudo -E bash "$0" "$@"
fi

require_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "ERROR: missing required file: $path" >&2
    exit 1
  fi
}

require_file "$REPO_ROOT/network_health_guard.py"
require_file "$REPO_ROOT/requirements.txt"
require_file "$REPO_ROOT/systemd/$SERVICE_NAME"
require_file "$REPO_ROOT/config/qarar-network-health.default"

if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --home-dir "$STATE_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi
if ! getent group "$SERVICE_GROUP" >/dev/null 2>&1; then
  groupadd --system "$SERVICE_GROUP"
fi
usermod -a -G "$SERVICE_GROUP" "$SERVICE_USER" >/dev/null 2>&1 || true

install -d -o root -g root -m 0755 "$INSTALL_ROOT"
install -d -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 0750 "$LOG_DIR" "$STATE_DIR"
rsync -a --delete \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude 'logs/*.jsonl' \
  "$REPO_ROOT/" "$INSTALL_ROOT/"

python3 -m venv "$INSTALL_ROOT/.venv"
"$INSTALL_ROOT/.venv/bin/python" -m pip install --upgrade pip >/tmp/qarar-pip-upgrade.log 2>&1 || true
if ! "$INSTALL_ROOT/.venv/bin/pip" install -r "$INSTALL_ROOT/requirements.txt" >/tmp/qarar-pip-install.log 2>&1; then
  echo "WARN: pip install failed. Guard is stdlib-only and service can still run." >&2
  echo "WARN: inspect /tmp/qarar-pip-install.log for package mirror/proxy issues." >&2
  if [[ "$STRICT_REQUIREMENTS" == "true" ]]; then
    exit 1
  fi
fi

install -o root -g root -m 0644 "$REPO_ROOT/config/qarar-network-health.default" /etc/default/qarar-network-health
install -o root -g root -m 0644 "$REPO_ROOT/systemd/$SERVICE_NAME" "/etc/systemd/system/$SERVICE_NAME"
touch "$LOG_DIR/network-health.jsonl"
chown "$SERVICE_USER:$SERVICE_GROUP" "$LOG_DIR/network-health.jsonl"
chmod 0640 "$LOG_DIR/network-health.jsonl"

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
if [[ "$START_SERVICE" == "true" ]]; then
  systemctl restart "$SERVICE_NAME"
fi
systemctl --no-pager --full status "$SERVICE_NAME" || true

echo "OK: installed $SERVICE_NAME"
echo "OK: config /etc/default/qarar-network-health"
echo "OK: log $LOG_DIR/network-health.jsonl"
