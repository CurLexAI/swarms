# Modal Cost Transition + Skills Compliance Plan (2026-05-24)

## Purpose
Provide a fast, low-overhead operational baseline so simple skills do not consume execution time unnecessarily, while enabling controlled migration away from always-on Modal cost.

## Verified Repository Facts
- Skill registry exists and already marks runtime activation as disabled (`runtime_activation: false`) across listed skills. (`.agents/registries/ai-skills.registry.yaml`)
- Modal provider exists as a backend adapter and requires env endpoints + `AGENT_API_TOKEN`. (`.agents/providers/modal_provider.py`)
- Operator CLI (`.agents/invoke.py`) currently documents/runs Modal-first calls for `mihwar`/`bayyinah` generation and review operations. (`.agents/invoke.py`)

## Commander Rule (Immediate)
For **simple skill-class tasks** (read-only inspection, docs formatting, basic checklists, static policy confirmation):
1. Do not call Modal runtime.
2. Do not block on external model inference.
3. Complete locally using repository evidence and local commands only.

Use Modal only for tasks that explicitly require model generation/review and where no local deterministic path exists.

## Transitional Runtime Policy
Adopt a three-state runtime mode for agent operations:

- `LOCAL_ONLY` (default for routine repository work)
  - No Modal call permitted.
  - Use local checks and deterministic scripts.

- `HYBRID_ON_DEMAND`
  - Modal calls allowed only when requested task explicitly depends on Mihwar/Bayyinah output.
  - Must record reason in execution report.

- `MODAL_REQUIRED`
  - Reserved for deployment validation, smoke probes, or runtime incidents.
  - Requires explicit operator intent per run.

## Verification Checklist (did agent apply skills correctly?)
Use this quick checklist after any delegated/skill-heavy run:

1. Confirm scope discipline:
   - `git status --short` contains only requested files.
2. Confirm no accidental runtime spend for simple tasks:
   - No `modal run` / `modal deploy` command used unless task demanded it.
3. Confirm skill alignment:
   - Task output references the relevant skill/policy files used.
4. Confirm evidence discipline:
   - Claims are backed by file + line references.

## Cost Guardrail (Operational)
If Modal endpoints have been unused for extended periods while billing continues:
1. Freeze non-essential Modal invocations (operate in `LOCAL_ONLY`).
2. Keep endpoint verification as scheduled/manual only.
3. Re-evaluate whether local runtime (or lower-cost provider) should replace always-on Modal for day-to-day work.

## Decision Log Entry Template
Use this in execution reports when runtime choice matters:

- Runtime mode selected: `LOCAL_ONLY | HYBRID_ON_DEMAND | MODAL_REQUIRED`
- Reason:
- Modal used: `YES/NO`
- If YES, command(s):
- If NO, local evidence commands:

## Current Recommendation
Set default operational posture to `LOCAL_ONLY` for routine skill-driven repository tasks, and move to `HYBRID_ON_DEMAND` only per explicit task need.
