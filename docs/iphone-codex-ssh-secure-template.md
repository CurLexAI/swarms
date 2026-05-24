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

## 4) iPhone Terminal Host Entry (Termius-style)

Use these fields:

- Label: `codex-prod`
- Hostname: `<server_ip_or_dns>`
- Port: `22`
- Username: `codexops`
- Authentication: `Key`
- Key: `iphone-ed25519`

Do **not** store privileged passwords in the app.

## 5) Optional Local SSH Config (Mac/Workstation)

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

## 6) Quick Verification Runbook

```bash
# from trusted client
ssh -i ~/.ssh/id_ed25519_codex codexops@<server_ip_or_dns> "hostname && whoami"

# on server, verify login events
sudo journalctl -u ssh --since "-30m" --no-pager
```

## 7) Sovereign Guardrails

- Keep sensitive workloads on private network/VPN only.
- Restrict Codex runtime account to least privilege.
- Rotate SSH keys periodically.
- Enable centralized audit logging before production use.
- Never expose private model endpoints or tokens in terminal history.
