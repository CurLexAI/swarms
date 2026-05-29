# iPhone → Codex SSH Secure Connection Template

## Purpose
Hardened SSH onboarding template for connecting iPhone terminal clients (e.g., Termius) to a Codex-controlled Linux runtime with sovereign security defaults.

## 1) Server Baseline (Ubuntu)

```bash
# 1. Create dedicated operator account
sudo adduser codexops
sudo usermod -aG sudo codexops

# 2. Prepare SSH directory
sudo -u codexops mkdir -p /home/codexops/.ssh
sudo -u codexops chmod 700 /home/codexops/.ssh
sudo -u codexops touch /home/codexops/.ssh/authorized_keys
sudo -u codexops chmod 600 /home/codexops/.ssh/authorized_keys

# 3. Add your iPhone public key (replace with real key)
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... iphone-codex" | sudo tee -a /home/codexops/.ssh/authorized_keys >/dev/null
sudo chown -R codexops:codexops /home/codexops/.ssh
```

## 2) SSH Daemon Hardening

`/etc/ssh/sshd_config`

```conf
Port 22
Protocol 2
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
PermitEmptyPasswords no
X11Forwarding no
AllowUsers codexops
MaxAuthTries 3
LoginGraceTime 30
ClientAliveInterval 300
ClientAliveCountMax 2
AllowTcpForwarding no
AllowAgentForwarding no
PermitTunnel no
```

Apply:

```bash
sudo sshd -t
sudo systemctl restart ssh
sudo systemctl status ssh --no-pager
```

## 3) Firewall Policy

```bash
# UFW example (allow only SSH)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw enable
sudo ufw status verbose
```

## 4) iPhone Terminal Host Entry (Quick Fill)

Use this exact mapping in the iPhone form:

- Display Name (اسم العرض): `swarms` or `Mihwer Codex`
- Host (المضيف): server address only, e.g. `123.45.67.89` or `your-server.com`
- Port (المنفذ): `22`
- Username (اسم المستخدم): server account, e.g. `ubuntu`, `root`, or `git`
- Password (كلمة المرور): server password, or leave blank when using SSH key authentication

## 5) iPhone Terminal Host Entry (Termius-style, hardened)

## 5) ChatGPT Codex iPhone SSH Workspace Recovery

Use this section when the iPhone Codex screen shows a message like: `Unable to connect to <workspace> via SSH. Check host name, port, network, password, and SSH service.`

### What the iPhone fields mean

The **workspace name** shown in ChatGPT, for example `Mihwer` or `Bayyinah-AI`, is only a label. It is not proof that SSH can resolve or reach a server. The SSH connection must still have a real reachable host, open port, valid username, valid authentication method, and a running SSH daemon.

Use this mapping:

| Codex/iPhone field | Safe value | Common failure |
|---|---|---|
| Workspace / Display name | Human label such as `Mihwer` | Treating the label as the server host |
| Host / Hostname | DNS name or IP address of the remote Linux runtime | Using an organization ID, workspace ID, repo name, or agent name |
| Port | `22`, unless the server is intentionally configured otherwise | Carrier/VPN/firewall blocks the port |
| Username | Linux account on the target host, for example `codexops` | GitHub/OpenAI account name instead of server user |
| Authentication | SSH key preferred; password only for temporary break-glass | Missing public key in `authorized_keys` or expired password |

### Recovery checklist

Run these checks from a trusted workstation or existing server session, not from the iPhone browser:

```bash
# 1. Confirm the target server SSH daemon is active
sudo systemctl status ssh --no-pager

# 2. Confirm sshd configuration is syntactically valid
sudo sshd -t

# 3. Confirm the server is listening on the expected port
ss -ltnp | grep ':22'

# 4. Confirm the operator account exists
id codexops

# 5. Confirm key directory permissions
sudo namei -l /home/codexops/.ssh/authorized_keys

# 6. Watch auth logs while pressing Retry in Codex on iPhone
sudo journalctl -u ssh --since '-10m' --no-pager
```

Expected interpretation:

- No log entry appears when pressing **Retry**: network path, DNS, host, port, VPN, firewall, or carrier path is wrong.
- Log says public key is rejected: wrong key selected on iPhone or missing public key in `authorized_keys`.
- Log says invalid user: the iPhone username does not exist on the server.
- Log says permission denied after authentication attempts: authentication method is wrong or disabled by `sshd_config`.
- SSH works from a laptop but not iPhone: check iPhone VPN/WireGuard profile, cellular restrictions, private relay, DNS profile, or app-specific key selection.

### Minimal safe fix sequence

```bash
# On the server, keep the change minimal and auditable.
sudo install -d -m 700 -o codexops -g codexops /home/codexops/.ssh
sudo touch /home/codexops/.ssh/authorized_keys
sudo chown codexops:codexops /home/codexops/.ssh/authorized_keys
sudo chmod 600 /home/codexops/.ssh/authorized_keys

# Paste only the iPhone PUBLIC key, never the private key.
sudoedit /home/codexops/.ssh/authorized_keys

# Validate before restart/reload.
sudo sshd -t
sudo systemctl reload ssh
```

Do not paste private SSH keys, passwords, API tokens, Modal endpoints, or OpenAI/GitHub tokens into ChatGPT, Codex, screenshots, issues, commits, or PRs.

### Canonical repository check after SSH works

Once the iPhone can connect to the remote host, run this from the SSH session before starting Codex work:

```bash
cd /workspace/swarms 2>/dev/null || cd ~/swarms
git remote -v
git status --short
git branch --show-current
python3 .agents/invoke.py info
```

Proceed only if the remote is the canonical `CurLexAI/swarms` repository and no unexpected local changes appear.

## 6) iPhone Terminal Host Entry (Termius-style, hardened)

Use these hardened fields when key-based auth is enabled:

- Label: `codex-prod`
- Hostname: `<server_ip_or_dns>`
- Port: `22`
- Username: `codexops`
- Authentication: `Key`
- Key: `iphone-ed25519`

Do **not** store privileged passwords in the app.

## 6) Optional Local SSH Config (Mac/Workstation)
## 7) Optional Local SSH Config (Mac/Workstation)

`~/.ssh/config`

```sshconfig
Host codex-prod
  HostName <server_ip_or_dns>
  User codexops
  Port 22
  IdentityFile ~/.ssh/id_ed25519_codex
  IdentitiesOnly yes
  PubkeyAuthentication yes
  PasswordAuthentication no
  ServerAliveInterval 60
  ServerAliveCountMax 2
  StrictHostKeyChecking yes
  UserKnownHostsFile ~/.ssh/known_hosts
```

## 7) Quick Verification Runbook
## 8) Quick Verification Runbook

```bash
# from trusted client
ssh -i ~/.ssh/id_ed25519_codex codexops@<server_ip_or_dns> "hostname && whoami"

# on server, verify login events
sudo journalctl -u ssh --since "-30m" --no-pager
```

## 8) Sovereign Guardrails
## 9) Sovereign Guardrails

- Keep sensitive workloads on private network/VPN only.
- Restrict Codex runtime account to least privilege.
- Rotate SSH keys periodically.
- Enable centralized audit logging before production use.
- Never expose private model endpoints or tokens in terminal history.

## 9) Use Your Computer from iPhone (Codex Computer Use)

Codex can operate your desktop environment from iPhone by using Computer Use sessions.

### Supported Operations

- Launch desktop applications on the connected workstation.
- Work inside authenticated web sessions in Chrome.
- Locate and use local files on the workstation.

### Safe Operating Pattern

1. Start Computer Use only on a trusted workstation (not shared/public hosts).
2. Keep session scope task-specific and time-bounded.
3. Do not open secrets vaults or private keys unless strictly required.
4. End the session immediately after the task and rotate temporary credentials if used.

### Minimum Security Controls

- Require MFA on the control account.
- Use device posture checks before granting remote control access.
- Keep audit logs for session start, actions, and termination.
- Restrict remote control to approved networks/VPN.

