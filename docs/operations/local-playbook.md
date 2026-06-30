# Local Deployment Playbook

## Prerequisites

- Docker Desktop
- Ollama
- Python 3.11+
- Node.js 20+

## Steps

### 1. Start Qdrant

```bash
docker compose -f deploy/qdrant/docker-compose.yml up -d
```

### 2. Start Ollama

```bash
ollama serve &
```


### 2.1 Activate the sovereign Ollama model set

The repository declares 18 local Ollama models in `config/ollama.local.models.json`. Verification is fail-closed and never calls external AI APIs. Pulling model weights is explicit because it can be large and must run only on the local model host.

```bash
# Verify only; fails if Ollama is down or any model is missing.
npm run ollama:verify-local

# Pull missing models, then verify all 18 models locally.
OLLAMA_PULL=1 npm run ollama:activate-local
```

### 3. Configure environment

```bash
export OLLAMA_BASE_URL=http://localhost:11434
export QDRANT_URL=http://localhost:6333
```

### 4. Install dependencies

```bash
pip install -r requirements-agent.txt
npm ci
```

### 5. Run agents smoke test

```bash
python3 .agents/invoke.py info
```

### 6. Run full test suite

```bash
python3 -m pytest -q tests/
npm test
```

### 7. Validate gates

```bash
npm run check
bash scripts/commander/adr-0001-boundary-gate.sh .
```
