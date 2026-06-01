# Dev Factory

Bootstrap a Windows development workstation with one command.

## What it installs
- Core development: Git, VS Code, Cursor, Windows Terminal, PowerShell 7, Docker Desktop, WSL2
- Engineering productivity: PowerToys, Everything, ShareX, Obsidian, Bruno, DBeaver, Figma
- Collaboration and docs: Outlook, Drawboard PDF, Inkodo, LiquidText
- Local databases via Docker Compose: PostgreSQL, Redis, MinIO, Qdrant, Ollama

## Quick start
Run PowerShell as Administrator:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
./scripts/bootstrap.ps1 -Profile full
```

Then start local services:

```powershell
docker compose -f ./config/docker-compose.yml up -d
node ./src/healthcheck.mjs
```

## Profiles
- `core`: essential engineering tools only
- `apps`: productivity and document tools
- `db`: Docker and local databases only
- `full`: everything

## Notes
- Some packages may prompt for sign-in or vendor setup.
- A reboot may be required after WSL and virtualization features are enabled.
- Run from an elevated PowerShell session for the smoothest setup.
