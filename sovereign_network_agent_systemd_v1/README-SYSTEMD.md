# Qarar Network Health Guard — systemd deployment

This package installs the Python-first Sovereign Network Agent as a safe Raspberry Pi service.

## Safe defaults

- `QARAR_NETWORK_DRY_RUN=true`
- `QARAR_ENABLE_ROUTER_REBOOT=false`
- log path: `/var/log/qarar-network-agent/network-health.jsonl`
- service user: `qarar-netguard`

## Install on Raspberry Pi

```bash
cd sovereign_network_agent_systemd_v1
bash scripts/pi/smoke-test-network-health-guard.sh
bash scripts/pi/install-qarar-network-health-service.sh
```

## Check status

```bash
bash scripts/pi/status-qarar-network-health-service.sh
```

## Uninstall service while preserving logs

```bash
bash scripts/pi/uninstall-qarar-network-health-service.sh
```

## Enable real actuation

Do not enable real actuation during the first 24-hour observation period.
Actuation requires all three conditions:

```bash
QARAR_NETWORK_DRY_RUN=false
QARAR_ENABLE_ROUTER_REBOOT=true
QARAR_ROUTER_REBOOT_COMMAND="/path/to/safe/reboot-command"
```

The service fails closed if the reboot command is missing.
