# Repository Command Sequences

## Scope and identity

```bash
pwd
git remote -v
git branch --show-current
git rev-parse HEAD
git status --short
```

## Agent inventory

```bash
find . -maxdepth 4 -type f \
  \( -path './.agents/*' -o -path './agents/*' -o -path './.github/agents/*' \) \
  | sort
```

## Python validation

```bash
python -m py_compile .agents/*.py
python -m unittest discover -s tests
```

## P0 security tests

```bash
bash scripts/commander/p0-security-test-gate.sh .
```

## Modal boundary

```bash
bash scripts/commander/modal-boundary-gate.sh .
```

## Agent presence

```bash
bash scripts/commander/agent-presence-gate.sh
```

## Modal smoke, only when secrets are configured

```bash
: "${BAYYINAH_ENDPOINT:?missing BAYYINAH_ENDPOINT}"
: "${MIHWAR_ENDPOINT:?missing MIHWAR_ENDPOINT}"
: "${AGENT_API_TOKEN:?missing AGENT_API_TOKEN}"
bash scripts/commander/modal-agent-smoke.sh
```

## Node validation, only when package.json exists

```bash
if [ -f package.json ]; then
  npm test
  npm audit --audit-level=high
else
  echo "NOT_APPLICABLE: package.json missing"
fi
```

## Secret safety

Do not paste secret values into chat, PR comments, logs, or artifacts. Report only `SET` or `UNSET`:

```bash
for v in BAYYINAH_ENDPOINT MIHWAR_ENDPOINT AGENT_API_TOKEN SOVEREIGN_API_KEY; do
  if [ -n "${!v:-}" ]; then echo "$v=SET"; else echo "$v=UNSET"; fi
done
```
