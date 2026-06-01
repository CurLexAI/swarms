# iPhone ↔ Remote Sync Troubleshooting (SSH)

Use this runbook when the iPhone client shows:

- "Waiting for Computer App"
- "Failed to connect via SSH"

## Quick command

```bash
bash scripts/commander/iphone-ssh-sync-diagnostic.sh <host> <port> <user>
```

Example:

```bash
bash scripts/commander/iphone-ssh-sync-diagnostic.sh 10.0.0.15 22 ubuntu
```

## What it validates

1. Local repository identity (`git remote`, branch, status).
2. Local agent syntax checks.
3. Agent inventory rendering.
4. DNS/TCP reachability to SSH host.
5. SSH handshake with non-interactive auth.
6. Remote repo state and ssh/sshd service activity.

## Safety boundaries

- Read-only diagnostics only.
- No secret output is requested.
- No deployment, merge, or production mutation.

## Common remediations

- Correct host/port/username in mobile connection profile.
- Ensure SSH service is running on remote machine.
- Open SSH port in firewall/security group.
- Ensure the remote path is `~/swarms` and points to canonical `CurLexAI/swarms`.
