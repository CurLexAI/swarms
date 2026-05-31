---
name: render-skills-catalog
description: Use when planning, installing, auditing, or operating Render AI agent skills in this repository without activating infrastructure or exposing secrets.
license: MIT
compatibility: Requires a Render account plus either Render CLI or Render MCP for live operations; repository use is catalog-only until credentials and operator authorization are present.
metadata:
  author: CurLexAI Platform Engineering
  upstream: https://github.com/render-oss/skills
  upstream_docs: https://render.com/docs
  version: "1.0.0"
  category: deployment
---

# Render Skills Catalog

## Purpose

Use this skill to map Render's official AI-agent skill catalog into CurLexAI's repository-controlled operating model. This skill is a **catalog and safety wrapper**, not a live Render activation. It helps an agent decide which upstream Render skill to install or consult while preserving the repository's secrets, network, and deployment boundaries.

## Sovereign Boundaries

- Do not deploy, restart, create, delete, or reconfigure Render resources unless the operator explicitly authorizes that infrastructure action.
- Do not print `RENDER_API_KEY`, `RENDER_API_TOKEN`, service IDs, private URLs, bearer tokens, logs containing secrets, or environment values.
- Do not add auto-approval hooks to Codex, Cursor, or OpenCode; upstream auto-approval hooks are Claude Code-only and still must not approve mutating infrastructure commands.
- Treat this repository as the control-plane source of truth. Do not copy external skills wholesale into `.agents/skills/` unless a separate intake task approves that import.
- Mark all live Render state as `UNVERIFIED` unless confirmed by Render CLI, Render MCP, dashboard export, or CI metadata in the current task.

## When to Use

Use this skill when the task mentions any of the following:

- installing or updating Render skills for an AI coding tool;
- selecting a Render skill for deploy, debug, monitor, scaling, domains, databases, or networking work;
- auditing whether Render operations are safe to perform from this repository;
- creating a plan for Render MCP or Render CLI usage without exposing credentials.

## Upstream Installation Options

Prefer the least invasive option that satisfies the task:

1. **Render CLI**: `render skills install` installs official Render skills into detected compatible tools.
2. **Interactive Render CLI**: `render skills`, `render skills list`, and `render skills update` manage installed skills.
3. **Skills CLI**: `npx skills add render-oss/skills` installs from the upstream repository.
4. **Manual copy**: copy selected directories from upstream `skills/` into a local client skills path such as `~/.codex/skills/`.

Do not run any installer in repository automation unless dependency and network policies have been reviewed for that specific task.

## Prerequisites for Live Operations

Before using Render CLI or Render MCP against real infrastructure, verify:

- a Render account is available;
- Render MCP is configured or Render CLI is installed;
- `RENDER_API_KEY` is present in the operator environment but never printed;
- the target application repository is connected to GitHub, GitLab, or Bitbucket for deploy-related skills;
- the task explicitly authorizes the relevant read-only or mutating operation.

## Catalog

### Get Started

| Skill | Use |
|---|---|
| `render-mcp` | Set up and troubleshoot the Render MCP server. |
| `render-cli` | Install and use the Render CLI for deploys, logs, SSH, and automation. |
| `render-deploy` | Deploy applications to Render. |
| `render-blueprints` | Author and validate `render.yaml` Blueprints. |

### Service Types

| Skill | Use |
|---|---|
| `render-web-services` | Configure public web services, health checks, and TLS. |
| `render-private-services` | Design internal-only services on Render's private network. |
| `render-static-sites` | Deploy static sites, SPAs, redirects, and custom headers. |
| `render-background-workers` | Set up queue-based background workers and graceful shutdown. |
| `render-cron-jobs` | Configure scheduled jobs and cron expressions. |
| `render-workflows` | Set up and develop Render Workflows. |

### Build and Runtime

| Skill | Use |
|---|---|
| `render-docker` | Build and deploy Docker-based services. |
| `render-env-vars` | Manage env vars, secrets, and env groups. |
| `render-disks` | Attach and manage persistent disks. |

### Networking and Access

| Skill | Use |
|---|---|
| `render-domains` | Configure custom domains and troubleshoot TLS. |
| `render-networking` | Connect services over Render's private network. |

### Data Services

| Skill | Use |
|---|---|
| `render-postgres` | Operate Managed PostgreSQL, backups, replicas, and connections. |
| `render-keyvalue` | Provision and tune Render Key Value. |

### Operate and Scale

| Skill | Use |
|---|---|
| `render-monitor` | Check service health, metrics, and logs. |
| `render-debug` | Diagnose failed deploys, startup issues, and runtime errors. |
| `render-scaling` | Configure autoscaling, instance sizing, and cost tradeoffs. |
| `render-migrate-from-heroku` | Migrate Heroku apps to Render. |

## Safe Operating Workflow

1. Classify the task as read-only, planning, or mutating infrastructure.
2. Select the smallest upstream Render skill that matches the task.
3. Check repository policies before any network, dependency, or Render command.
4. For read-only commands, redact service identifiers and secret-like values from reports.
5. For mutating commands, require explicit operator authorization and a rollback plan.
6. Record evidence with `VERIFIED`, `INFERRED`, or `UNVERIFIED` labels.

## Read-Only Command Examples

These examples are read-only, but they still require a configured Render CLI and authenticated operator environment:

```bash
render skills list
render workspace current
render services list
render logs --raw
```

## Blocked Without Explicit Authorization

Do not run these classes of commands unless the operator explicitly asks for that live infrastructure change:

- deploy, redeploy, restart, suspend, resume, or delete services;
- create or modify env vars, secret files, disks, domains, scaling, cron schedules, or Blueprints;
- upload logs or raw repository diffs to third-party services;
- install hooks that bypass human review for mutating operations.

## Reporting Template

```text
VERIFIED:
INFERRED:
UNVERIFIED:
RENDER_SKILL_SELECTED:
COMMANDS_RUN:
SECRETS_EXPOSURE: NONE | REDACTED | BLOCKED
NEXT_ACTION:
```
