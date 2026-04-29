# legal-compliance Skill Intake Plan

## Scope Lock
- **Objective:** intake and validate a provided `legal-compliance` Codex skill package before operational use.
- **In scope:** package structure validation, installation path, runtime smoke checks, and usage playbooks.
- **Out of scope:** legal advice assertions, production compliance certification, or external API integration.

## Canonical Skill Package (provided)

```text
legal-compliance/
├── SKILL.md
├── agents/
│   └── openai.yaml
└── references/
    ├── privacy-regulations.md
    ├── dpa-review.md
    ├── data-subject-requests.md
    └── regulatory-monitoring.md
```

## Plan of Record

1. **Establish runtime truth**
   - Confirm repository branch and clean working tree.
   - Confirm skill intake target path under local skills home.

2. **Establish canonical path**
   - Install the skill from the provided zip using `skill-installer` workflow.
   - Confirm final location contains `SKILL.md`, `agents/openai.yaml`, and all reference files.

3. **Detect blockers**
   - Fail with `CONFIG_NOT_FOUND` if required files are missing.
   - Fail with `SYNTAX_FAILURE` if YAML cannot parse.
   - Mark `UNVERIFIED_RUNTIME` if runtime services are unavailable.

4. **Detect hot-surface conflicts**
   - Verify no other skill with the same name (`legal-compliance`) is already active with conflicting metadata.
   - Verify no workflow override changes existing global skill loading behavior.

5. **Apply minimal correct change**
   - Add only skill assets and any minimal index/registry entry required by this repository.
   - Avoid unrelated refactors in adapters, workflows, or deploy paths.

6. **Verify actual impact**
   - Check skill discovery output includes `legal-compliance`.
   - Run representative prompts:
     - DPA review for GDPR Article 28 gaps, transfer risk, breach notification, and processor obligations.
     - Data subject deletion request triage, deadline calculation, verification steps, exemptions, and response drafting.

7. **Status reporting contract**
   - Use only: `VERIFIED_FIXED`, `PARTIALLY_APPLIED`, `CHANGED_BUT_NOT_VERIFIED`, `BLOCKED`, `UNVERIFIED`, `NOT_STARTED`, `SUPERSEDED`, `CONFLICTED`.

## Intake Checklist

- [ ] `legal-compliance/SKILL.md` exists and is readable.
- [ ] `legal-compliance/agents/openai.yaml` parses without error.
- [ ] All four reference markdown files exist.
- [ ] Skill is discoverable via the local skill listing command.
- [ ] DPA review prompt runs and returns structured severity levels.
- [ ] DSR deletion prompt runs and returns classification + deadline + draft response.

## Optional Enhancement (recommended)

Add:

```text
references/saudi-privacy-regulatory.md
```

to track PDPL, NCA, SAMA, and CST obligations independently from global privacy references.
