# Qarar/Bayyinah Sovereign Command Notebook

## Purpose

This notebook is an operator archive for the Qarar/Bayyinah/Mihwar sovereign agent-control platform. It is intentionally documentation-only: it does not alter runtime behavior, deployment settings, secrets, or CI/CD.

## Evidence Discipline

Every operational claim in this notebook uses exactly one evidence label:

- `VERIFIED` — Confirmed by observable repository content or a command executed in this checkout.
- `INFERRED` — Reasonable conclusion from repository evidence, but not directly proven by a live runtime check.
- `UNVERIFIED` — Not checked in this session, blocked by missing runtime/secrets, or dependent on an operator environment.

## Architecture Map

```text
[SAMA] -> [Fetcher] -> [Parser] -> [Auditor/Gate] -> [Qdrant] -> [Model Router] -> [Ollama/llama.cpp]
                                                        |
                                                        v
                                                  [Audit Trail]
```

## Component Inventory

| Component | Path | Evidence Status | Notes |
|---|---|---:|---|
| Agent operations repository | `README.md` | VERIFIED | The repository identifies itself as the private operator repository for Qarar/Bayyinah/Mihwar agent operations. |
| Docker composition | `docker-compose.yml` | VERIFIED | File exists in this checkout; live container execution remains operator-side. |
| SAMA fetcher agent | `sama_ingestion_swarm/agent_fetcher.py` | VERIFIED | File exists in this checkout. |
| SAMA parser agent | `sama_ingestion_swarm/agent_parser.py` | VERIFIED | File exists in this checkout. |
| SAMA auditor agent | `sama_ingestion_swarm/agent_auditor.py` | VERIFIED | File exists in this checkout. |
| Classification policy | `src/core/classification.py` | VERIFIED | File exists in this checkout. |
| Sovereign model router | `src/core/model_router.py` | VERIFIED | File exists in this checkout. |
| Audited router wrapper | `src/core/audited_router.py` | VERIFIED | File exists in this checkout. |
| Local Ollama provider | `src/providers/local_ollama.py` | VERIFIED | File exists in this checkout. |
| Local llama.cpp provider | `src/providers/local_llama_cpp.py` | VERIFIED | File exists in this checkout. |
| Aegis MCP gateway | `.agents/mcp/aegis_gateway.py` | VERIFIED | File exists in this checkout. |
| Legacy Aegis verifier path | `scripts/verify_aegis.py` | UNVERIFIED | The file is not present in this checkout; use repository validation gates listed below instead. |
| Mobile gate path | `mobile-gate/` | UNVERIFIED | The directory is not present in this checkout. |
| `qarar-security-gate/` path | `qarar-security-gate/` | UNVERIFIED | The directory is not present in this checkout. |

## Local Validation Commands

Run these from the repository root after installing dependencies according to repository policy.

```bash
# Validate agent repository assets without external services.
python3 .agents/validate.py

# Syntax-check Python agent files.
python3 -m py_compile .agents/*.py

# Show configured agents without requiring runtime secrets.
python3 .agents/invoke.py info

# Run the aggregate Node/repository gate.
npm run check

# Run Python tests.
python3 -m pytest -q tests/

# Run Node unit tests that do not require backend integration secrets.
npm run test:unit

# Run security-focused Node tests.
npm run test:security
```

## Live Docker Runtime Proof

The following commands prove the local container runtime path only when executed on an operator machine with Docker, model assets, and service configuration available.

```bash
# Start local services.
docker compose up -d

# Test Ollama with a local prompt.
docker compose exec ollama ollama run deepseek-r1:8b "عاصمة السعودية؟"

# Test llama.cpp health from inside the llama-server service.
docker compose exec llama-server curl -s http://localhost:8080/health
```

Status: `UNVERIFIED` in this session. The commands above must be executed on the live operator runtime before any production-ready runtime claim is made.

## Zero-Trust Operating Principles

- `INFERRED` — Sensitive data must remain inside the operator-controlled environment unless a classified egress review explicitly authorizes transfer.
- `INFERRED` — External API keys are not required for local Ollama or local llama.cpp inference paths.
- `INFERRED` — Audit trails must be append-only or integrity-checked before they can be used as evidence.
- `VERIFIED` — The classification precedence in code is `RESTRICTED > CONFIDENTIAL > INTERNAL > PUBLIC` when enforced by the repository classification module and tests.

## Google Drive Sync Agent for Colab

Use this script in Google Colab from a workspace that already contains a checked-out repository copy. It preserves source-relative paths under the dated backup directory and avoids copying missing files silently.

```python
# Qarar Google Drive sync agent for Colab.
from google.colab import auth, drive
from pathlib import Path
import datetime
import shutil

# 1. Authenticate and mount Drive.
auth.authenticate_user()
drive.mount("/content/drive")

# 2. Configure repository root and destination.
DATE = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")
REPO_ROOT = Path.cwd()
DEST_DIR = Path("/content/drive/MyDrive/Qarar_Backups") / DATE
DEST_DIR.mkdir(parents=True, exist_ok=True)

# 3. Critical files to archive.
FILES_TO_SYNC = [
    "Qarar_Command_Notebook.md",
    "docker-compose.yml",
    ".agents/mcp/aegis_gateway.py",
    "src/core/classification.py",
    "src/core/model_router.py",
    "src/core/audited_router.py",
    "src/providers/local_ollama.py",
    "src/providers/local_llama_cpp.py",
    "sama_ingestion_swarm/agent_fetcher.py",
    "sama_ingestion_swarm/agent_parser.py",
    "sama_ingestion_swarm/agent_auditor.py",
]

# 4. Copy files while preserving relative paths.
for relative_path in FILES_TO_SYNC:
    source = REPO_ROOT / relative_path
    destination = DEST_DIR / relative_path
    if source.exists() and source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        print(f"✅ copied: {relative_path}")
    else:
        print(f"⚠️ missing: {relative_path}")

print(f"\n🎉 sync complete: {DEST_DIR}")
```

## Archive Checklist

- `VERIFIED` — Notebook file exists in the repository after this change.
- `VERIFIED` — Notebook avoids committing secrets or private endpoint URLs.
- `UNVERIFIED` — Live Docker proof remains pending until the operator runs the Docker commands above.
- `UNVERIFIED` — Google Drive sync remains pending until the Colab script is executed by an authenticated operator.

## Next Operator Action

Run the live Docker proof commands on the operator machine and record the exact output in a dated launch-evidence note before changing the runtime status from `UNVERIFIED` to `VERIFIED`.
