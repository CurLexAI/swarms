---
name: modal-runtime-operator
description: operate the backend-only modal runtime for mihwar and bayyinah agents. use when deploying or updating `.agents/modal_app.py`, checking modal secrets, verifying `BAYYINAH_ENDPOINT`, `MIHWAR_ENDPOINT`, `BAYYINAH_API_TOKEN`, `MIHWAR_API_TOKEN`, running smoke tests, or proving whether private agent runtime is active. never expose modal urls to browser, iphone, frontend, or public client surfaces.
---

# Modal Runtime Operator

## Commands

Run from repository root:

```bash
python3 -m py_compile .agents/*.py
python3 .agents/validate.py
python3 .agents/invoke.py info

bash scripts/commander/p0-security-test-gate.sh .
bash scripts/commander/modal-boundary-gate.sh .
bash scripts/commander/adr-0001-boundary-gate.sh .
bash scripts/commander/agent-presence-gate.sh .

modal deploy .agents/modal_app.py
```

## Secret handling

Report only:

```text
BAYYINAH_ENDPOINT=SET|UNSET
MIHWAR_ENDPOINT=SET|UNSET
BAYYINAH_API_TOKEN=SET|UNSET
MIHWAR_API_TOKEN=SET|UNSET
```

Never print values.

## Readiness rule

Runtime is `UNVERIFIED` until endpoint smoke tests pass.

## Verdicts

* READY: deploy succeeded and smoke tests passed.
* HOLD: local gates pass but runtime smoke tests are missing.
* BLOCK: CRITICAL/HIGH security or boundary failure.
* UNVERIFIED: cannot inspect required runtime state.
