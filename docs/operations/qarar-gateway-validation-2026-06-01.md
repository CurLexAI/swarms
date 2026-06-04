# Qarar Gateway Validation Evidence — 2026-06-01
Execution Verdict:
- Status: VERIFIED backend gateway candidate only; not production-ready.
- Scope: Qarar gateway PR validation output requested before approval.
- Canonical Path: /workspace/swarms
- Files Touched: docs/operations/qarar-gateway-validation-2026-06-01.md
- Blockers: None for backend gateway candidate validation; Modal runtime secrets remain intentionally absent in local no-secrets mode.
- Hot Surface Risk: Backend gateway surface only; no public/client Modal endpoint exposure was approved.
- What Was Actually Changed: Added exact local validation output evidence for PR body use.
- What Was Actually Verified: Python compile, targeted Qarar tests, npm checks/tests, ADR boundary, Modal boundary, and repository static secret scan.
- What Remains Unverified: Production readiness, live Modal/Bayyinah/Mihwar runtime activation, external secret presence, and deployment behavior.
- Next Valid Action: Paste this exact validation output into the PR body and keep the PR marked backend gateway candidate only.

VERIFIED:
- Required validation commands were run from `/workspace/swarms` on 2026-06-01.

CHANGED:
- Added this validation evidence report only.

VALIDATION:
- All required commands exited 0.
- `modal-boundary-gate.sh` emitted expected local no-secrets warnings for missing runtime secrets while still returning PASS.

RISKS:
- This evidence does not approve production deployment or live agent activation.

DECISION:
- Backend gateway candidate only; not production-ready.

NEXT ACTION:
- Update the PR body with the exact output below.

## Exact validation output

### 1. Python compile

```text
$ python -m py_compile .agents/mcp/qarar_api_server.py tests/test_qarar_api_server.py tests/test_qarar_api_server_security.py

[exit status: 0]
```

### 2. Qarar pytest suite

```text
$ pytest -q tests/test_qarar_api_server.py tests/test_qarar_api_server_security.py
........................                                                 [100%]
24 passed in 1.87s

[exit status: 0]
```

### 3. npm aggregate check

```text
$ npm run check --if-present
npm warn Unknown env config "http-proxy". This will stop working in the next major version of npm.

> curlexai-swarms@1.0.0 check
> npm run check:service-divergence && npm run test:unit && npm run check:boundary && npm run check:cdn-sri && npm run check:audit-integrity && npm run check:swarms-presence && npm run check:supabase-boundary && npm run check:runtime-policy && npm run test:runtime-policy

npm warn Unknown env config "http-proxy". This will stop working in the next major version of npm.

> curlexai-swarms@1.0.0 check:service-divergence
> node scripts/check-service-divergence.mjs

Service divergence check passed.
npm warn Unknown env config "http-proxy". This will stop working in the next major version of npm.

> curlexai-swarms@1.0.0 test:unit
> node --test tests/unifiedAgentAdapter.test.js

TAP version 13
# Subtest: forwardToPythonEngine guards missing PYTHON_BACKEND_URL with CONFIG_NOT_FOUND and structured log
ok 1 - forwardToPythonEngine guards missing PYTHON_BACKEND_URL with CONFIG_NOT_FOUND and structured log
  ---
  duration_ms: 14.443565
  ...
# Subtest: loadRegistry logs loaded and reasoning-enabled counters for mixed definitions
ok 2 - loadRegistry logs loaded and reasoning-enabled counters for mixed definitions
  ---
  duration_ms: 1.953701
  ...
# Subtest: loadRegistry supports primary and fallback registry paths and accepts dict-keyed agents
ok 3 - loadRegistry supports primary and fallback registry paths and accepts dict-keyed agents
  ---
  duration_ms: 2.219067
  ...
# Subtest: node dispatcher CONFIG_NOT_FOUND is limited to the canonical agentRunner module
ok 4 - node dispatcher CONFIG_NOT_FOUND is limited to the canonical agentRunner module
  ---
  duration_ms: 1.417196
  ...
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 2,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] Registry startup integrity check {
#   registryPathSource: 'env',
#   registryPath: '/tmp/registry-test-Bylnsf/registry.yaml'
# }
# [ERROR] ❌ Registry Integrity Breach {
#   err: RegistryStartupError: REGISTRY_LOAD_FAILURE: Invalid agent entry at index 0 (expected object)
#       at UnifiedAgentAdapter.loadRegistry (file:///workspace/swarms/src/services/unifiedAgentAdapter.js:356:31)
#       at new UnifiedAgentAdapter (file:///workspace/swarms/src/services/unifiedAgentAdapter.js:325:14)
#       at file:///workspace/swarms/tests/unifiedAgentAdapter.test.js:106:11
#       at getActual (node:assert:498:5)
#       at Function.throws (node:assert:644:24)
#       at TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.test.js:105:10)
#       at async Test.run (node:internal/test_runner/test:797:9)
#       at async Test.processPendingSubtests (node:internal/test_runner/test:526:7) {
#     code: 'REGISTRY_LOAD_FAILURE',
#     registryPath: '/tmp/registry-test-Bylnsf/registry.yaml'
#   },
#   registryPath: '/tmp/registry-test-Bylnsf/registry.yaml',
#   failurePhase: 'schema_or_io',
#   failureCode: 'REGISTRY_LOAD_FAILURE'
# }
# Subtest: loadRegistry runtime: invalid array entries trigger startup failure and unhealthy service
ok 5 - loadRegistry runtime: invalid array entries trigger startup failure and unhealthy service
  ---
  duration_ms: 91.931453
  ...
# Subtest: loadRegistry array path validates schema and fails fast instead of skipping entries
ok 6 - loadRegistry array path validates schema and fails fast instead of skipping entries
  ---
  duration_ms: 0.914964
  ...
# Subtest: live .agents/config/agents.yaml declares mihwar/bayyinah and matches Modal deployment
ok 7 - live .agents/config/agents.yaml declares mihwar/bayyinah and matches Modal deployment
  ---
  duration_ms: 13.257624
  ...
1..7
# tests 7
# suites 0
# pass 7
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 489.592647
npm warn Unknown env config "http-proxy". This will stop working in the next major version of npm.

> curlexai-swarms@1.0.0 check:boundary
> bash scripts/commander/adr-0001-boundary-gate.sh .

[INFO] ADR-0001 boundary gate
[INFO] repo=/workspace/swarms
[OK]   no autoStart activation flag detected
[RESULT] PASS
npm warn Unknown env config "http-proxy". This will stop working in the next major version of npm.

> curlexai-swarms@1.0.0 check:cdn-sri
> node scripts/check-cdn-sri.mjs

All HTTPS script tags include integrity and crossorigin="anonymous".
npm warn Unknown env config "http-proxy". This will stop working in the next major version of npm.

> curlexai-swarms@1.0.0 check:audit-integrity
> bash scripts/commander/qala-audit-integrity-gate.sh .

[qala-audit-integrity-gate] VERIFY: TypeScript/Node Qala audit chain
TAP version 13
# Subtest: first record chains from GENESIS
ok 1 - first record chains from GENESIS
  ---
  duration_ms: 14.386556
  ...
# Subtest: subsequent records chain correctly
ok 2 - subsequent records chain correctly
  ---
  duration_ms: 3.118775
  ...
# Subtest: verifyChain passes for a clean log
ok 3 - verifyChain passes for a clean log
  ---
  duration_ms: 3.199845
  ...
# Subtest: modifying a payload breaks the chain
ok 4 - modifying a payload breaks the chain
  ---
  duration_ms: 3.041541
  ...
# Subtest: modifying prev_hash breaks the chain
ok 5 - modifying prev_hash breaks the chain
  ---
  duration_ms: 2.769609
  ...
# Subtest: rejects unknown event
ok 6 - rejects unknown event
  ---
  duration_ms: 1.324332
  ...
# Subtest: rejects missing trace id
ok 7 - rejects missing trace id
  ---
  duration_ms: 9.161978
  ...
# Subtest: rejects missing tenant
ok 8 - rejects missing tenant
  ---
  duration_ms: 1.304975
  ...
# Subtest: payload defaults to empty object
ok 9 - payload defaults to empty object
  ---
  duration_ms: 3.736797
  ...
# Subtest: append-only API has no update / delete
ok 10 - append-only API has no update / delete
  ---
  duration_ms: 1.530405
  ...
# Subtest: payload key order does not change the hash
ok 11 - payload key order does not change the hash
  ---
  duration_ms: 2.427187
  ...
1..11
# tests 11
# suites 0
# pass 11
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 456.034304
[qala-audit-integrity-gate] VERIFY: Python Qala audit chain
..............
----------------------------------------------------------------------
Ran 14 tests in 0.016s

OK
[qala-audit-integrity-gate] PASS: Qala audit append-only hash-chain integrity verified
[INFO] Qal'a audit integrity gate (Q7)
[INFO] repo=/workspace/swarms
AUDIT_SINK_PATH: /workspace/swarms/artifacts/security/qala-audit.jsonl
AUDIT_CHAIN_OK records_verified=0
[OK]   audit chain intact
[RESULT] PASS
npm warn Unknown env config "http-proxy". This will stop working in the next major version of npm.

> curlexai-swarms@1.0.0 check:swarms-presence
> python3 scripts/commander/swarm-presence-monitor.py --repo-root . --no-network

{
  "checks": [
    {
      "detail": "required control files exist",
      "evidence": {
        "count": 8
      },
      "name": "static repository controls",
      "status": "VERIFIED"
    },
    {
      "detail": "boundary, modal, agent-presence, and aegis gates are present",
      "evidence": {},
      "name": "static validation gates",
      "status": "VERIFIED"
    },
    {
      "detail": "running inside a Git worktree",
      "evidence": {},
      "name": "git worktree identity",
      "status": "VERIFIED"
    },
    {
      "detail": "network checks disabled",
      "evidence": {},
      "name": "GitHub repository metadata",
      "status": "SKIPPED_UNVERIFIED"
    },
    {
      "detail": "network checks disabled",
      "evidence": {},
      "name": "MCP health",
      "status": "SKIPPED_UNVERIFIED"
    },
    {
      "detail": "network checks disabled",
      "evidence": {},
      "name": "Microsoft Entra metadata",
      "status": "SKIPPED_UNVERIFIED"
    }
  ],
  "exitCode": 0,
  "generatedAt": "2026-06-01T16:31:35.297406+00:00",
  "repo": "CurLexAI/swarms",
  "strict": false,
  "summary": {
    "FAILED": 0,
    "HOLD": 0,
    "SKIPPED_UNVERIFIED": 3,
    "VERIFIED": 3
  }
}
npm warn Unknown env config "http-proxy". This will stop working in the next major version of npm.

> curlexai-swarms@1.0.0 check:supabase-boundary
> node scripts/check-supabase-public-boundary.mjs

Supabase public/client boundary passed (8 files scanned).
npm warn Unknown env config "http-proxy". This will stop working in the next major version of npm.

> curlexai-swarms@1.0.0 check:runtime-policy
> tsx scripts/check-runtime-policy.ts

✅ runtime architecture blocks retired primary modes: VERIFIED
✅ restricted runtime remains local-control-plane only: VERIFIED
✅ confidential policy excludes external cloud: VERIFIED
✅ public vision requires human-approved cloud egress: VERIFIED
✅ invalid classification fails closed: VERIFIED
Runtime policy check passed.
npm warn Unknown env config "http-proxy". This will stop working in the next major version of npm.

> curlexai-swarms@1.0.0 test:runtime-policy
> node --import tsx --test tests/runtime-policy.test.ts

TAP version 13
# Subtest: canonical policy rejects invalid legacy classification
ok 1 - canonical policy rejects invalid legacy classification
  ---
  duration_ms: 3.112076
  ...
# Subtest: RESTRICTED data is local-control-plane only
ok 2 - RESTRICTED data is local-control-plane only
  ---
  duration_ms: 2.269621
  ...
# Subtest: public burst can use approved/external providers only with human approval
ok 3 - public burst can use approved/external providers only with human approval
  ---
  duration_ms: 0.670313
  ...
# Subtest: public code long-context can use Cursor only with human approval
ok 4 - public code long-context can use Cursor only with human approval
  ---
  duration_ms: 0.790577
  ...
# Subtest: public vision fails closed without human-approved cloud egress
ok 5 - public vision fails closed without human-approved cloud egress
  ---
  duration_ms: 0.62873
  ...
# Subtest: public vision uses approved Llama 4 cloud only after human approval
ok 6 - public vision uses approved Llama 4 cloud only after human approval
  ---
  duration_ms: 0.531633
  ...
# Subtest: deprecated runtimePolicy adapter delegates to canonical provider ids
ok 7 - deprecated runtimePolicy adapter delegates to canonical provider ids
  ---
  duration_ms: 0.817028
  ...
# Subtest: deprecated runtimePolicy adapter blocks retired legacy cloud mode
ok 8 - deprecated runtimePolicy adapter blocks retired legacy cloud mode
  ---
  duration_ms: 0.733976
  ...
1..8
# tests 8
# suites 0
# pass 8
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 1168.066122

[exit status: 0]
```

### 4. npm test

```text
$ npm test --if-present
npm warn Unknown env config "http-proxy". This will stop working in the next major version of npm.

> curlexai-swarms@1.0.0 test
> node --test tests/unifiedAgentAdapter.test.js tests/unifiedAgentAdapter.executeAgent.non2xx.integration.test.js tests/unifiedAgentAdapter.nodeDispatch.integration.test.js

TAP version 13
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [AUDIT] {"event":"agent_task_init","status":"PENDING","timestamp":"2026-06-01T16:31:47.697Z","taskId":"13f82c45-ffe7-42fc-afe2-4ef6dab0a4d1","tenant_id":"tenant-1","actor_id":"user-1","agent_id":"py-agent","metadata":{"correlation_id":"bac94639-40ae-433b-9fbf-85ecd44a027a","task_id":"13f82c45-ffe7-42fc-afe2-4ef6dab0a4d1","agent":{"id":"py-agent","name":"Python Agent","runtime":"python","capabilities":["python_execution"],"reasoning_enabled":false},"request_metadata":{"source":"integration-test"}}}
# [ERROR] 💥 Intelligence Failure at Agent py-agent {
#   err: PythonEngineRuntimeError: RUNTIME_FAILURE: Python engine returned HTTP 500 unknown
#       at createPythonRuntimeError (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331507629.d1affb81eb31e.mjs:218:12)
#       at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331507629.d1affb81eb31e.mjs:779:27)
#       at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331507629.d1affb81eb31e.mjs:590:19)
#       at async waitForActual (node:assert:533:5)
#       at async Function.rejects (node:assert:654:25)
#       at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.executeAgent.non2xx.integration.test.js:133:3)
#       at async Test.run (node:internal/test_runner/test:797:9)
#       at async Test.processPendingSubtests (node:internal/test_runner/test:526:7) {
#     code: 'RUNTIME_FAILURE',
#     upstreamStatus: 500,
#     retryable: false
#   },
#   agentId: 'py-agent',
#   structuredFailure: {
#     failure_class: 'RUNTIME_FAILURE',
#     upstream_status: 500,
#     retryable: false
#   },
#   normalizedError: {
#     message: 'RUNTIME_FAILURE: Python engine returned HTTP 500 unknown',
#     code: 'RUNTIME_FAILURE',
#     stack: 'PythonEngineRuntimeError: RUNTIME_FAILURE: Python engine returned HTTP 500 unknown\\n' +
#       '    at createPythonRuntimeError (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331507629.d1affb81eb31e.mjs:218:12)\\n' +
#       '    at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331507629.d1affb81eb31e.mjs:779:27)\\n' +
#       '    at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.178...[truncated]'
#   },
#   originalStack: 'PythonEngineRuntimeError: RUNTIME_FAILURE: Python engine returned HTTP 500 unknown\\n' +
#     '    at createPythonRuntimeError (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331507629.d1affb81eb31e.mjs:218:12)\\n' +
#     '    at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331507629.d1affb81eb31e.mjs:779:27)\\n' +
#     '    at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331507629.d1affb81eb31e.mjs:590:19)\\n' +
#     '    at async waitForActual (node:assert:533:5)\\n' +
#     '    at async Function.rejects (node:assert:654:25)\\n' +
#     '    at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.executeAgent.non2xx.integration.test.js:133:3)\\n' +
#     '    at async Test.run (node:internal/test_runner/test:797:9)\\n' +
#     '    at async Test.processPendingSubtests (node:internal/test_runner/test:526:7)'
# }
# Subtest: UnifiedAgentAdapter.executeAgent marks task FAILED and throws sanitized client-safe error on non-2xx python response
ok 1 - UnifiedAgentAdapter.executeAgent marks task FAILED and throws sanitized client-safe error on non-2xx python response
  ---
  duration_ms: 2479.274357
  ...
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [AUDIT] {"event":"agent_task_init","status":"PENDING","timestamp":"2026-06-01T16:31:48.131Z","taskId":"d1fcd91b-6a82-4c57-a8e9-d34179c39d90","tenant_id":"tenant-1","actor_id":"user-1","agent_id":"py-agent","metadata":{"correlation_id":"5948e3ba-49ce-455f-82dd-763b6446df39","task_id":"d1fcd91b-6a82-4c57-a8e9-d34179c39d90","agent":{"id":"py-agent","name":"Python Agent","runtime":"python","capabilities":["python_execution"],"reasoning_enabled":false},"request_metadata":{"source":"integration-test"}}}
# [ERROR] Python engine fetch failed {
#   classification: 'RUNTIME_FAILURE',
#   stage: 'python_engine_fetch',
#   attempt: 1,
#   maxAttempts: 2,
#   timeoutMs: 15000,
#   retryable: false,
#   errorName: 'Error',
#   errorCode: null,
#   causeName: null,
#   causeCode: null
# }
# [ERROR] 💥 Intelligence Failure at Agent py-agent {
#   err: PythonEngineRuntimeError: RUNTIME_FAILURE: python engine request transport failure
#       at createPythonRuntimeError (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331508107.b100099a609ae.mjs:218:12)
#       at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331508107.b100099a609ae.mjs:825:23)
#       at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331508107.b100099a609ae.mjs:590:19)
#       at async waitForActual (node:assert:533:5)
#       ... 3 lines matching cause stack trace ...
#       at async Test.processPendingSubtests (node:internal/test_runner/test:526:7) {
#     code: 'RUNTIME_FAILURE',
#     upstreamStatus: 502,
#     retryable: false,
#     cause: Error: connect ECONNREFUSED python-backend.internal
#         at global.fetch (file:///workspace/swarms/tests/unifiedAgentAdapter.executeAgent.non2xx.integration.test.js:181:11)
#         at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331508107.b100099a609ae.mjs:760:40)
#         at UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331508107.b100099a609ae.mjs:590:30)
#         at async waitForActual (node:assert:533:5)
#         at async Function.rejects (node:assert:654:25)
#         at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.executeAgent.non2xx.integration.test.js:214:3)
#         at async Test.run (node:internal/test_runner/test:797:9)
#         at async Test.processPendingSubtests (node:internal/test_runner/test:526:7)
#   },
#   agentId: 'py-agent',
#   structuredFailure: {
#     failure_class: 'RUNTIME_FAILURE',
#     upstream_status: 502,
#     retryable: false
#   },
#   normalizedError: {
#     message: 'RUNTIME_FAILURE: python engine request transport failure',
#     code: 'RUNTIME_FAILURE',
#     stack: 'PythonEngineRuntimeError: RUNTIME_FAILURE: python engine request transport failure\\n' +
#       '    at createPythonRuntimeError (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331508107.b100099a609ae.mjs:218:12)\\n' +
#       '    at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331508107.b100099a609ae.mjs:825:23)\\n' +
#       '    at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.178...[truncated]'
#   },
#   originalStack: 'PythonEngineRuntimeError: RUNTIME_FAILURE: python engine request transport failure\\n' +
#     '    at createPythonRuntimeError (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331508107.b100099a609ae.mjs:218:12)\\n' +
#     '    at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331508107.b100099a609ae.mjs:825:23)\\n' +
#     '    at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331508107.b100099a609ae.mjs:590:19)\\n' +
#     '    at async waitForActual (node:assert:533:5)\\n' +
#     '    at async Function.rejects (node:assert:654:25)\\n' +
#     '    at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.executeAgent.non2xx.integration.test.js:214:3)\\n' +
#     '    at async Test.run (node:internal/test_runner/test:797:9)\\n' +
#     '    at async Test.processPendingSubtests (node:internal/test_runner/test:526:7)'
# }
# Subtest: UnifiedAgentAdapter.executeAgent maps network errors to sanitized 502 contract
ok 2 - UnifiedAgentAdapter.executeAgent maps network errors to sanitized 502 contract
  ---
  duration_ms: 426.469021
  ...
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [AUDIT] {"event":"agent_task_init","status":"PENDING","timestamp":"2026-06-01T16:31:48.355Z","taskId":"9a8d302a-e835-42ab-aa8e-9d9c94ff6313","tenant_id":"tenant-1","actor_id":"user-1","agent_id":"py-agent","metadata":{"correlation_id":"683c2bf6-ec8a-4752-b3ce-ea660770684d","task_id":"9a8d302a-e835-42ab-aa8e-9d9c94ff6313","agent":{"id":"py-agent","name":"Python Agent","runtime":"python","capabilities":["python_execution"],"reasoning_enabled":false},"request_metadata":{}}}
# [ERROR] Python engine fetch failed {
#   classification: 'RUNTIME_FAILURE',
#   stage: 'python_engine_fetch',
#   attempt: 1,
#   maxAttempts: 2,
#   timeoutMs: 15000,
#   retryable: true,
#   errorName: 'TypeError',
#   errorCode: null,
#   causeName: 'Error',
#   causeCode: 'ENOTFOUND'
# }
# [ERROR] Python engine fetch failed {
#   classification: 'RUNTIME_FAILURE',
#   stage: 'python_engine_fetch',
#   attempt: 2,
#   maxAttempts: 2,
#   timeoutMs: 15000,
#   retryable: true,
#   errorName: 'TypeError',
#   errorCode: null,
#   causeName: 'Error',
#   causeCode: 'ENOTFOUND'
# }
# [ERROR] 💥 Intelligence Failure at Agent py-agent {
#   err: PythonEngineRuntimeError: RUNTIME_FAILURE: python engine request transport failure
#       at createPythonRuntimeError (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331508336.0f804ede5f197.mjs:218:12)
#       at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331508336.0f804ede5f197.mjs:825:23)
#       at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331508336.0f804ede5f197.mjs:590:19)
#       ... 4 lines matching cause stack trace ...
#       at async Test.processPendingSubtests (node:internal/test_runner/test:526:7) {
#     code: 'RUNTIME_FAILURE',
#     upstreamStatus: 502,
#     retryable: false,
#     cause: TypeError: fetch failed
#         at global.fetch (file:///workspace/swarms/tests/unifiedAgentAdapter.executeAgent.non2xx.integration.test.js:275:17)
#         at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331508336.0f804ede5f197.mjs:760:40)
#         ... 5 lines matching cause stack trace ...
#         at async Test.processPendingSubtests (node:internal/test_runner/test:526:7) {
#       cause: [Error]
#     }
#   },
#   agentId: 'py-agent',
#   structuredFailure: {
#     failure_class: 'RUNTIME_FAILURE',
#     upstream_status: 502,
#     retryable: false
#   },
#   normalizedError: {
#     message: 'RUNTIME_FAILURE: python engine request transport failure',
#     code: 'RUNTIME_FAILURE',
#     stack: 'PythonEngineRuntimeError: RUNTIME_FAILURE: python engine request transport failure\\n' +
#       '    at createPythonRuntimeError (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331508336.0f804ede5f197.mjs:218:12)\\n' +
#       '    at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331508336.0f804ede5f197.mjs:825:23)\\n' +
#       '    at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.178...[truncated]'
#   },
#   originalStack: 'PythonEngineRuntimeError: RUNTIME_FAILURE: python engine request transport failure\\n' +
#     '    at createPythonRuntimeError (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331508336.0f804ede5f197.mjs:218:12)\\n' +
#     '    at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331508336.0f804ede5f197.mjs:825:23)\\n' +
#     '    at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331508336.0f804ede5f197.mjs:590:19)\\n' +
#     '    at async waitForActual (node:assert:533:5)\\n' +
#     '    at async Function.rejects (node:assert:654:25)\\n' +
#     '    at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.executeAgent.non2xx.integration.test.js:319:3)\\n' +
#     '    at async Test.run (node:internal/test_runner/test:797:9)\\n' +
#     '    at async Test.processPendingSubtests (node:internal/test_runner/test:526:7)'
# }
# Subtest: UnifiedAgentAdapter.executeAgent retries fetch failed errors with ENOTFOUND cause and keeps client errors sanitized
ok 3 - UnifiedAgentAdapter.executeAgent retries fetch failed errors with ENOTFOUND cause and keeps client errors sanitized
  ---
  duration_ms: 474.305307
  ...
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [AUDIT] {"event":"agent_task_init","status":"PENDING","timestamp":"2026-06-01T16:31:48.798Z","taskId":"5e5f2c5f-9c1d-4aa2-9bbb-53e814fd9960","tenant_id":"tenant-1","actor_id":"user-1","agent_id":"py-agent","metadata":{"correlation_id":"de997baf-ab5d-418f-91c7-099b97da3453","task_id":"5e5f2c5f-9c1d-4aa2-9bbb-53e814fd9960","agent":{"id":"py-agent","name":"Python Agent","runtime":"python","capabilities":["python_execution"],"reasoning_enabled":false},"request_metadata":{}}}
# [ERROR] Python engine fetch failed {
#   classification: 'RUNTIME_FAILURE',
#   stage: 'python_engine_fetch',
#   attempt: 1,
#   maxAttempts: 2,
#   timeoutMs: 15000,
#   retryable: true,
#   errorName: 'TypeError',
#   errorCode: null,
#   causeName: 'Error',
#   causeCode: 'ECONNREFUSED'
# }
# Subtest: UnifiedAgentAdapter.executeAgent retries fetch failed errors with ECONNREFUSED cause and keeps client errors sanitized
ok 4 - UnifiedAgentAdapter.executeAgent retries fetch failed errors with ECONNREFUSED cause and keeps client errors sanitized
  ---
  duration_ms: 442.436763
  ...
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [AUDIT] {"event":"agent_task_init","status":"PENDING","timestamp":"2026-06-01T16:31:49.323Z","taskId":"8b83bb54-9e3b-4ab9-8cad-18888b87ceff","tenant_id":"tenant-1","actor_id":"user-1","agent_id":"py-agent","metadata":{"correlation_id":"61bedd26-ab9e-4878-8bda-c5f1993666c4","task_id":"8b83bb54-9e3b-4ab9-8cad-18888b87ceff","agent":{"id":"py-agent","name":"Python Agent","runtime":"python","capabilities":["python_execution"],"reasoning_enabled":false},"request_metadata":{"source":"integration-test"}}}
# [ERROR] 💥 Intelligence Failure at Agent py-agent {
#   err: PythonEngineRuntimeError: Python engine request failed with status 200. Please try again later (ref: 108b274f).
#       at createPythonRuntimeError (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331509299.ac64abdc4caba.mjs:218:12)
#       at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331509299.ac64abdc4caba.mjs:786:27)
#       at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331509299.ac64abdc4caba.mjs:590:19)
#       at async waitForActual (node:assert:533:5)
#       at async Function.rejects (node:assert:654:25)
#       at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.executeAgent.non2xx.integration.test.js:461:3)
#       at async Test.run (node:internal/test_runner/test:797:9)
#       at async Test.processPendingSubtests (node:internal/test_runner/test:526:7) {
#     code: 'UNVERIFIED_RUNTIME',
#     upstreamStatus: 200,
#     retryable: false
#   },
#   agentId: 'py-agent',
#   structuredFailure: {
#     failure_class: 'UNVERIFIED_RUNTIME',
#     upstream_status: 200,
#     retryable: false
#   },
#   normalizedError: {
#     message: 'Python engine request failed with status 200. Please try again later (ref: 108b274f).',
#     code: 'UNVERIFIED_RUNTIME',
#     stack: 'PythonEngineRuntimeError: Python engine request failed with status 200. Please try again later (ref: 108b274f).\\n' +
#       '    at createPythonRuntimeError (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331509299.ac64abdc4caba.mjs:218:12)\\n' +
#       '    at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331509299.ac64abdc4caba.mjs:786:27)\\n' +
#       '    at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unif...[truncated]'
#   },
#   originalStack: 'PythonEngineRuntimeError: Python engine request failed with status 200. Please try again later (ref: 108b274f).\\n' +
#     '    at createPythonRuntimeError (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331509299.ac64abdc4caba.mjs:218:12)\\n' +
#     '    at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331509299.ac64abdc4caba.mjs:786:27)\\n' +
#     '    at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331509299.ac64abdc4caba.mjs:590:19)\\n' +
#     '    at async waitForActual (node:assert:533:5)\\n' +
#     '    at async Function.rejects (node:assert:654:25)\\n' +
#     '    at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.executeAgent.non2xx.integration.test.js:461:3)\\n' +
#     '    at async Test.run (node:internal/test_runner/test:797:9)\\n' +
#     '    at async Test.processPendingSubtests (node:internal/test_runner/test:526:7)'
# }
# Subtest: UnifiedAgentAdapter.executeAgent rejects successful non-JSON python responses with sanitized runtime error
ok 5 - UnifiedAgentAdapter.executeAgent rejects successful non-JSON python responses with sanitized runtime error
  ---
  duration_ms: 286.711291
  ...
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [AUDIT] {"event":"agent_task_init","status":"PENDING","timestamp":"2026-06-01T16:31:49.547Z","taskId":"f5f9822d-c05b-4bd1-b972-37122fcc7119","tenant_id":"tenant-1","actor_id":"user-1","agent_id":"py-agent","metadata":{"correlation_id":"0f62e09d-5f6a-4d0e-876d-277cc5222cf6","task_id":"f5f9822d-c05b-4bd1-b972-37122fcc7119","agent":{"id":"py-agent","name":"Python Agent","runtime":"python","capabilities":["python_execution"],"reasoning_enabled":false},"request_metadata":{}}}
# [ERROR] 💥 Intelligence Failure at Agent py-agent {
#   err: PythonEngineRuntimeError: RUNTIME_FAILURE: Python engine returned HTTP 503 unknown
#       at createPythonRuntimeError (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331509524.7841f333cf73e.mjs:218:12)
#       at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331509524.7841f333cf73e.mjs:779:27)
#       at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331509524.7841f333cf73e.mjs:590:19)
#       at async waitForActual (node:assert:533:5)
#       at async Function.rejects (node:assert:654:25)
#       at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.executeAgent.non2xx.integration.test.js:530:3)
#       at async Test.run (node:internal/test_runner/test:797:9)
#       at async Test.processPendingSubtests (node:internal/test_runner/test:526:7) {
#     code: 'RUNTIME_FAILURE',
#     upstreamStatus: 503,
#     retryable: true
#   },
#   agentId: 'py-agent',
#   structuredFailure: {
#     failure_class: 'RUNTIME_FAILURE',
#     upstream_status: 503,
#     retryable: true
#   },
#   normalizedError: {
#     message: 'RUNTIME_FAILURE: Python engine returned HTTP 503 unknown',
#     code: 'RUNTIME_FAILURE',
#     stack: 'PythonEngineRuntimeError: RUNTIME_FAILURE: Python engine returned HTTP 503 unknown\\n' +
#       '    at createPythonRuntimeError (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331509524.7841f333cf73e.mjs:218:12)\\n' +
#       '    at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331509524.7841f333cf73e.mjs:779:27)\\n' +
#       '    at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.178...[truncated]'
#   },
#   originalStack: 'PythonEngineRuntimeError: RUNTIME_FAILURE: Python engine returned HTTP 503 unknown\\n' +
#     '    at createPythonRuntimeError (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331509524.7841f333cf73e.mjs:218:12)\\n' +
#     '    at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331509524.7841f333cf73e.mjs:779:27)\\n' +
#     '    at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331509524.7841f333cf73e.mjs:590:19)\\n' +
#     '    at async waitForActual (node:assert:533:5)\\n' +
#     '    at async Function.rejects (node:assert:654:25)\\n' +
#     '    at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.executeAgent.non2xx.integration.test.js:530:3)\\n' +
#     '    at async Test.run (node:internal/test_runner/test:797:9)\\n' +
#     '    at async Test.processPendingSubtests (node:internal/test_runner/test:526:7)'
# }
# Subtest: UnifiedAgentAdapter.executeAgent retries retryable 503 responses up to PYTHON_BACKEND_MAX_ATTEMPTS total attempts
ok 6 - UnifiedAgentAdapter.executeAgent retries retryable 503 responses up to PYTHON_BACKEND_MAX_ATTEMPTS total attempts
  ---
  duration_ms: 963.976922
  ...
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [AUDIT] {"event":"agent_task_init","status":"PENDING","timestamp":"2026-06-01T16:31:50.498Z","taskId":"8b5fc1a3-7b59-4aff-be27-002b12bb7775","tenant_id":"tenant-1","actor_id":"user-1","agent_id":"py-agent","metadata":{"correlation_id":"cfb7b4ea-7e97-40e1-aa7a-cd2296a3ba97","task_id":"8b5fc1a3-7b59-4aff-be27-002b12bb7775","agent":{"id":"py-agent","name":"Python Agent","runtime":"python","capabilities":["python_execution"],"reasoning_enabled":false},"request_metadata":{}}}
# [ERROR] 💥 Intelligence Failure at Agent py-agent {
#   err: PythonEngineRuntimeError: RUNTIME_FAILURE: Python engine returned HTTP 503 unknown
#       at createPythonRuntimeError (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331510485.e417d86065d5.mjs:218:12)
#       at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331510485.e417d86065d5.mjs:779:27)
#       at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331510485.e417d86065d5.mjs:590:19)
#       at async waitForActual (node:assert:533:5)
#       at async Function.rejects (node:assert:654:25)
#       at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.executeAgent.non2xx.integration.test.js:575:3)
#       at async Test.run (node:internal/test_runner/test:797:9)
#       at async Test.processPendingSubtests (node:internal/test_runner/test:526:7) {
#     code: 'RUNTIME_FAILURE',
#     upstreamStatus: 503,
#     retryable: true
#   },
#   agentId: 'py-agent',
#   structuredFailure: {
#     failure_class: 'RUNTIME_FAILURE',
#     upstream_status: 503,
#     retryable: true
#   },
#   normalizedError: {
#     message: 'RUNTIME_FAILURE: Python engine returned HTTP 503 unknown',
#     code: 'RUNTIME_FAILURE',
#     stack: 'PythonEngineRuntimeError: RUNTIME_FAILURE: Python engine returned HTTP 503 unknown\\n' +
#       '    at createPythonRuntimeError (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331510485.e417d86065d5.mjs:218:12)\\n' +
#       '    at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331510485.e417d86065d5.mjs:779:27)\\n' +
#       '    at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.17803...[truncated]'
#   },
#   originalStack: 'PythonEngineRuntimeError: RUNTIME_FAILURE: Python engine returned HTTP 503 unknown\\n' +
#     '    at createPythonRuntimeError (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331510485.e417d86065d5.mjs:218:12)\\n' +
#     '    at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331510485.e417d86065d5.mjs:779:27)\\n' +
#     '    at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331510485.e417d86065d5.mjs:590:19)\\n' +
#     '    at async waitForActual (node:assert:533:5)\\n' +
#     '    at async Function.rejects (node:assert:654:25)\\n' +
#     '    at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.executeAgent.non2xx.integration.test.js:575:3)\\n' +
#     '    at async Test.run (node:internal/test_runner/test:797:9)\\n' +
#     '    at async Test.processPendingSubtests (node:internal/test_runner/test:526:7)'
# }
# Subtest: UnifiedAgentAdapter.executeAgent performs a single outbound attempt for retryable 503 when PYTHON_BACKEND_MAX_ATTEMPTS=1
ok 7 - UnifiedAgentAdapter.executeAgent performs a single outbound attempt for retryable 503 when PYTHON_BACKEND_MAX_ATTEMPTS=1
  ---
  duration_ms: 195.39442
  ...
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [AUDIT] {"event":"agent_task_init","status":"PENDING","timestamp":"2026-06-01T16:31:50.681Z","taskId":"ff29ca75-e3c5-4d2d-bb71-a3e7b6ef596e","tenant_id":"tenant-1","actor_id":"user-1","agent_id":"py-agent","metadata":{"correlation_id":"474d8a66-d24d-448b-a17d-3ef23a844341","task_id":"ff29ca75-e3c5-4d2d-bb71-a3e7b6ef596e","agent":{"id":"py-agent","name":"Python Agent","runtime":"python","capabilities":["python_execution"],"reasoning_enabled":false},"request_metadata":{}}}
# [AUDIT] {"event":"agent_task_status","taskId":"ff29ca75-e3c5-4d2d-bb71-a3e7b6ef596e","status":"RUNNING","result":{"correlation_id":"474d8a66-d24d-448b-a17d-3ef23a844341","task_id":"ff29ca75-e3c5-4d2d-bb71-a3e7b6ef596e","agent":{"id":"py-agent","name":"Python Agent","runtime":"python","capabilities":["python_execution"],"reasoning_enabled":false}}}
# [AUDIT] {"event":"agent_action","tenant_id":"tenant-1","actor_id":"user-1","agent_id":"py-agent","action":"EXECUTE_PYTHON_WITHOUT_REASONING","payload":{"taskId":"ff29ca75-e3c5-4d2d-bb71-a3e7b6ef596e","correlation_id":"474d8a66-d24d-448b-a17d-3ef23a844341","reasoning_enabled":false},"metadata":{"correlation_id":"474d8a66-d24d-448b-a17d-3ef23a844341","task_id":"ff29ca75-e3c5-4d2d-bb71-a3e7b6ef596e","agent":{"id":"py-agent","name":"Python Agent","runtime":"python","capabilities":["python_execution"],"reasoning_enabled":false}},"redaction_version":"1"}
# [AUDIT] {"event":"agent_task_status","taskId":"ff29ca75-e3c5-4d2d-bb71-a3e7b6ef596e","status":"FAILED","result":{"error":"CONFIG_NOT_FOUND: PYTHON_BACKEND_ALLOWED_HOSTS is required when strict backend allowlist mode is enabled","stack":"Error: CONFIG_NOT_FOUND: PYTHON_BACKEND_ALLOWED_HOSTS is required when strict backend allowlist mode is enabled\\n    at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331510604.300a1d58b8f03.mjs:751:19)\\n    at UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331510604.300a1d58b8f03.mjs:590:30)\\n    at async waitForActual (node:assert:533:5)\\n    at async Function.rejects (nod...[truncated]","blocker":"CONFIG_NOT_FOUND","failure_class":"CONFIG_NOT_FOUND","upstream_status":null}}
# [ERROR] 💥 Intelligence Failure at Agent py-agent {
#   err: Error: CONFIG_NOT_FOUND: PYTHON_BACKEND_ALLOWED_HOSTS is required when strict backend allowlist mode is enabled
#       at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331510604.300a1d58b8f03.mjs:751:19)
#       at UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331510604.300a1d58b8f03.mjs:590:30)
#       at async waitForActual (node:assert:533:5)
#       at async Function.rejects (node:assert:654:25)
#       at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.executeAgent.non2xx.integration.test.js:611:3)
#       at async Test.run (node:internal/test_runner/test:797:9)
#       at async Test.processPendingSubtests (node:internal/test_runner/test:526:7),
#   agentId: 'py-agent',
#   structuredFailure: { failure_class: 'CONFIG_NOT_FOUND', upstream_status: null },
#   normalizedError: {
#     message: 'CONFIG_NOT_FOUND: PYTHON_BACKEND_ALLOWED_HOSTS is required when strict backend allowlist mode is enabled',
#     stack: 'Error: CONFIG_NOT_FOUND: PYTHON_BACKEND_ALLOWED_HOSTS is required when strict backend allowlist mode is enabled\\n' +
#       '    at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331510604.300a1d58b8f03.mjs:751:19)\\n' +
#       '    at UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331510604.300a1d58b8f03.mjs:590:30)\\n' +
#       '    at async waitForActual (node:assert:533:5)\\n' +
#       '    at async Function.rejects (nod...[truncated]'
#   },
#   originalStack: 'Error: CONFIG_NOT_FOUND: PYTHON_BACKEND_ALLOWED_HOSTS is required when strict backend allowlist mode is enabled\\n' +
#     '    at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331510604.300a1d58b8f03.mjs:751:19)\\n' +
#     '    at UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331510604.300a1d58b8f03.mjs:590:30)\\n' +
#     '    at async waitForActual (node:assert:533:5)\\n' +
#     '    at async Function.rejects (node:assert:654:25)\\n' +
#     '    at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.executeAgent.non2xx.integration.test.js:611:3)\\n' +
#     '    at async Test.run (node:internal/test_runner/test:797:9)\\n' +
#     '    at async Test.processPendingSubtests (node:internal/test_runner/test:526:7)'
# }
# Subtest: UnifiedAgentAdapter.executeAgent blocks forwarding in strict mode when allowlist is empty
ok 8 - UnifiedAgentAdapter.executeAgent blocks forwarding in strict mode when allowlist is empty
  ---
  duration_ms: 182.559523
  ...
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [AUDIT] {"event":"agent_task_init","status":"PENDING","timestamp":"2026-06-01T16:31:50.821Z","taskId":"cf6c65da-16e6-4384-aaf5-45ec92bb917c","tenant_id":"tenant-1","actor_id":"user-1","agent_id":"py-agent","metadata":{"correlation_id":"4ca1e0c7-e4e3-46d0-81b3-935362c91296","task_id":"cf6c65da-16e6-4384-aaf5-45ec92bb917c","agent":{"id":"py-agent","name":"Python Agent","runtime":"python","capabilities":["python_execution"],"reasoning_enabled":false},"request_metadata":{}}}
# [AUDIT] {"event":"agent_task_status","taskId":"cf6c65da-16e6-4384-aaf5-45ec92bb917c","status":"RUNNING","result":{"correlation_id":"4ca1e0c7-e4e3-46d0-81b3-935362c91296","task_id":"cf6c65da-16e6-4384-aaf5-45ec92bb917c","agent":{"id":"py-agent","name":"Python Agent","runtime":"python","capabilities":["python_execution"],"reasoning_enabled":false}}}
# [AUDIT] {"event":"agent_action","tenant_id":"tenant-1","actor_id":"user-1","agent_id":"py-agent","action":"EXECUTE_PYTHON_WITHOUT_REASONING","payload":{"taskId":"cf6c65da-16e6-4384-aaf5-45ec92bb917c","correlation_id":"4ca1e0c7-e4e3-46d0-81b3-935362c91296","reasoning_enabled":false},"metadata":{"correlation_id":"4ca1e0c7-e4e3-46d0-81b3-935362c91296","task_id":"cf6c65da-16e6-4384-aaf5-45ec92bb917c","agent":{"id":"py-agent","name":"Python Agent","runtime":"python","capabilities":["python_execution"],"reasoning_enabled":false}},"redaction_version":"1"}
# [AUDIT] {"event":"agent_task_status","taskId":"cf6c65da-16e6-4384-aaf5-45ec92bb917c","status":"FAILED","result":{"error":"CONFIG_NOT_FOUND: PYTHON_BACKEND_URL must use HTTPS","stack":"Error: CONFIG_NOT_FOUND: PYTHON_BACKEND_URL must use HTTPS\\n    at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331510808.90b0f0895abf6.mjs:751:19)\\n    at UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331510808.90b0f0895abf6.mjs:590:30)\\n    at async waitForActual (node:assert:533:5)\\n    at async Function.rejects (node:assert:654:25)\\n    at async TestContext.<anonymous>...[truncated]","blocker":"CONFIG_NOT_FOUND","failure_class":"CONFIG_NOT_FOUND","upstream_status":null}}
# [ERROR] 💥 Intelligence Failure at Agent py-agent {
#   err: Error: CONFIG_NOT_FOUND: PYTHON_BACKEND_URL must use HTTPS
#       at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331510808.90b0f0895abf6.mjs:751:19)
#       at UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331510808.90b0f0895abf6.mjs:590:30)
#       at async waitForActual (node:assert:533:5)
#       at async Function.rejects (node:assert:654:25)
#       at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.executeAgent.non2xx.integration.test.js:639:3)
#       at async Test.run (node:internal/test_runner/test:797:9)
#       at async Test.processPendingSubtests (node:internal/test_runner/test:526:7),
#   agentId: 'py-agent',
#   structuredFailure: { failure_class: 'CONFIG_NOT_FOUND', upstream_status: null },
#   normalizedError: {
#     message: 'CONFIG_NOT_FOUND: PYTHON_BACKEND_URL must use HTTPS',
#     stack: 'Error: CONFIG_NOT_FOUND: PYTHON_BACKEND_URL must use HTTPS\\n' +
#       '    at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331510808.90b0f0895abf6.mjs:751:19)\\n' +
#       '    at UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331510808.90b0f0895abf6.mjs:590:30)\\n' +
#       '    at async waitForActual (node:assert:533:5)\\n' +
#       '    at async Function.rejects (node:assert:654:25)\\n' +
#       '    at async TestContext.<anonymous>...[truncated]'
#   },
#   originalStack: 'Error: CONFIG_NOT_FOUND: PYTHON_BACKEND_URL must use HTTPS\\n' +
#     '    at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331510808.90b0f0895abf6.mjs:751:19)\\n' +
#     '    at UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331510808.90b0f0895abf6.mjs:590:30)\\n' +
#     '    at async waitForActual (node:assert:533:5)\\n' +
#     '    at async Function.rejects (node:assert:654:25)\\n' +
#     '    at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.executeAgent.non2xx.integration.test.js:639:3)\\n' +
#     '    at async Test.run (node:internal/test_runner/test:797:9)\\n' +
#     '    at async Test.processPendingSubtests (node:internal/test_runner/test:526:7)'
# }
# Subtest: UnifiedAgentAdapter.executeAgent blocks non-https backend URLs in strict mode
ok 9 - UnifiedAgentAdapter.executeAgent blocks non-https backend URLs in strict mode
  ---
  duration_ms: 139.744917
  ...
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [AUDIT] {"event":"agent_task_init","status":"PENDING","timestamp":"2026-06-01T16:31:50.948Z","taskId":"25422a37-a91a-40a3-abb7-12cf862d7ef0","tenant_id":"tenant-1","actor_id":"user-1","agent_id":"py-agent","metadata":{"correlation_id":"640756c8-e084-4850-967d-a34346583880","task_id":"25422a37-a91a-40a3-abb7-12cf862d7ef0","agent":{"id":"py-agent","name":"Python Agent","runtime":"python","capabilities":["python_execution"],"reasoning_enabled":false},"request_metadata":{}}}
# Subtest: UnifiedAgentAdapter.executeAgent allows strict mode forwarding when host is allowlisted and https
ok 10 - UnifiedAgentAdapter.executeAgent allows strict mode forwarding when host is allowlisted and https
  ---
  duration_ms: 125.213695
  ...
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [ERROR] 💥 Intelligence Failure at Agent py-agent {
#   err: PythonEngineRuntimeError: Python engine timed out after 15000ms for agent py-agent
#       at createPythonRuntimeError (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331511036.ed97d18cdeb5c.mjs:218:12)
#       at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331511036.ed97d18cdeb5c.mjs:800:27)
#       at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331511036.ed97d18cdeb5c.mjs:590:19)
#       at async waitForActual (node:assert:533:5)
#       at async Function.rejects (node:assert:654:25)
#       at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.executeAgent.non2xx.integration.test.js:726:3)
#       at async Test.run (node:internal/test_runner/test:797:9)
#       at async Test.processPendingSubtests (node:internal/test_runner/test:526:7) {
#     code: 'PYTHON_ENGINE_TIMEOUT',
#     upstreamStatus: null,
#     retryable: false,
#     cause: Error [AbortError]: The operation was aborted
#         at TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.executeAgent.non2xx.integration.test.js:702:36)
#         at async Test.run (node:internal/test_runner/test:797:9)
#         at async Test.processPendingSubtests (node:internal/test_runner/test:526:7)
#   },
#   agentId: 'py-agent',
#   structuredFailure: {
#     failure_class: 'PYTHON_ENGINE_TIMEOUT',
#     upstream_status: null,
#     retryable: false
#   },
#   normalizedError: {
#     message: 'Python engine timed out after 15000ms for agent py-agent',
#     code: 'PYTHON_ENGINE_TIMEOUT',
#     stack: 'PythonEngineRuntimeError: Python engine timed out after 15000ms for agent py-agent\\n' +
#       '    at createPythonRuntimeError (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331511036.ed97d18cdeb5c.mjs:218:12)\\n' +
#       '    at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331511036.ed97d18cdeb5c.mjs:800:27)\\n' +
#       '    at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.178...[truncated]'
#   },
#   originalStack: 'PythonEngineRuntimeError: Python engine timed out after 15000ms for agent py-agent\\n' +
#     '    at createPythonRuntimeError (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331511036.ed97d18cdeb5c.mjs:218:12)\\n' +
#     '    at UnifiedAgentAdapter.forwardToPythonEngine (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331511036.ed97d18cdeb5c.mjs:800:27)\\n' +
#     '    at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.test.7269.1780331511036.ed97d18cdeb5c.mjs:590:19)\\n' +
#     '    at async waitForActual (node:assert:533:5)\\n' +
#     '    at async Function.rejects (node:assert:654:25)\\n' +
#     '    at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.executeAgent.non2xx.integration.test.js:726:3)\\n' +
#     '    at async Test.run (node:internal/test_runner/test:797:9)\\n' +
#     '    at async Test.processPendingSubtests (node:internal/test_runner/test:526:7)'
# }
# Subtest: UnifiedAgentAdapter.executeAgent maps AbortError timeout to PYTHON_ENGINE_TIMEOUT and marks task FAILED
ok 11 - UnifiedAgentAdapter.executeAgent maps AbortError timeout to PYTHON_ENGINE_TIMEOUT and marks task FAILED
  ---
  duration_ms: 121.882124
  ...
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# Subtest: UnifiedAgentAdapter dispatches node runtime to canonical runAgent with validated payload
ok 12 - UnifiedAgentAdapter dispatches node runtime to canonical runAgent with validated payload
  ---
  duration_ms: 2638.60657
  ...
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [ERROR] 💥 Intelligence Failure at Agent node-agent {
#   err: RuntimeOutputVerificationError: UNVERIFIED_RUNTIME: downstream payload failed verification (required runtime output field is missing or malformed)
#       at UnifiedAgentAdapter.verifyOutputQuality (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331508173.e76c3a443a246.mjs:692:19)
#       at UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331508173.e76c3a443a246.mjs:592:47)
#       at async waitForActual (node:assert:533:5)
#       at async Function.rejects (node:assert:654:25)
#       at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.nodeDispatch.integration.test.js:226:3)
#       at async Test.run (node:internal/test_runner/test:797:9)
#       at async Test.processPendingSubtests (node:internal/test_runner/test:526:7) {
#     code: 'UNVERIFIED_RUNTIME',
#     reason: 'required runtime output field is missing or malformed'
#   },
#   agentId: 'node-agent',
#   structuredFailure: { failure_class: 'UNVERIFIED_RUNTIME', upstream_status: null },
#   normalizedError: {
#     message: 'UNVERIFIED_RUNTIME: downstream payload failed verification (required runtime output field is missing or malformed)',
#     code: 'UNVERIFIED_RUNTIME',
#     stack: 'RuntimeOutputVerificationError: UNVERIFIED_RUNTIME: downstream payload failed verification (required runtime output field is missing or malformed)\\n' +
#       '    at UnifiedAgentAdapter.verifyOutputQuality (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331508173.e76c3a443a246.mjs:692:19)\\n' +
#       '    at UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331508173.e76c3a443a246.mjs:592:47)\\n' +
#       '    at async waitForActual (no...[truncated]'
#   },
#   originalStack: 'RuntimeOutputVerificationError: UNVERIFIED_RUNTIME: downstream payload failed verification (required runtime output field is missing or malformed)\\n' +
#     '    at UnifiedAgentAdapter.verifyOutputQuality (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331508173.e76c3a443a246.mjs:692:19)\\n' +
#     '    at UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331508173.e76c3a443a246.mjs:592:47)\\n' +
#     '    at async waitForActual (node:assert:533:5)\\n' +
#     '    at async Function.rejects (node:assert:654:25)\\n' +
#     '    at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.nodeDispatch.integration.test.js:226:3)\\n' +
#     '    at async Test.run (node:internal/test_runner/test:797:9)\\n' +
#     '    at async Test.processPendingSubtests (node:internal/test_runner/test:526:7)'
# }
# Subtest: UnifiedAgentAdapter rejects malformed downstream object that passes JSON parsing but fails quality verification
ok 13 - UnifiedAgentAdapter rejects malformed downstream object that passes JSON parsing but fails quality verification
  ---
  duration_ms: 309.305545
  ...
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [AUDIT] {"event":"agent_task_init","status":"PENDING","timestamp":"2026-06-01T16:31:48.396Z","taskId":"10a1a63f-edaf-43c4-8e20-a2db0e244f97","tenant_id":"tenant-1","actor_id":"user-1","agent_id":"hybrid-agent","metadata":{"correlation_id":"e686ab2a-58bc-4d0a-a14e-cac63ba58403","task_id":"10a1a63f-edaf-43c4-8e20-a2db0e244f97","agent":{"id":"hybrid-agent","name":"Hybrid Agent","runtime":"hybrid","capabilities":["node_execution"],"reasoning_enabled":false},"request_metadata":{"mode":"hybrid"}}}
# Subtest: UnifiedAgentAdapter returns real node execution output for hybrid agents (intentional split)
ok 14 - UnifiedAgentAdapter returns real node execution output for hybrid agents (intentional split)
  ---
  duration_ms: 199.699051
  ...
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [AUDIT] {"event":"agent_task_init","status":"PENDING","timestamp":"2026-06-01T16:31:48.555Z","taskId":"b8262cd2-3b22-418c-a298-124fda2f0045","tenant_id":"tenant-1","actor_id":"user-1","agent_id":"node-agent","metadata":{"correlation_id":"307066a3-10cf-4c5a-884f-ca68b4b024ee","task_id":"b8262cd2-3b22-418c-a298-124fda2f0045","agent":{"id":"node-agent","name":"Node Agent","runtime":"node","capabilities":["node_execution"],"reasoning_enabled":false},"request_metadata":{}}}
# Subtest: UnifiedAgentAdapter accepts valid downstream payload when quality verification requirements are met
ok 15 - UnifiedAgentAdapter accepts valid downstream payload when quality verification requirements are met
  ---
  duration_ms: 159.508401
  ...
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [AUDIT] {"event":"agent_task_init","status":"PENDING","timestamp":"2026-06-01T16:31:48.825Z","taskId":"37de25c5-deeb-49fb-9519-080ff10e8e32","tenant_id":"tenant-1","actor_id":"user-1","agent_id":"node-agent","metadata":{"correlation_id":"e7df0441-90f8-4061-9b6c-ac9b8b3018ec","task_id":"37de25c5-deeb-49fb-9519-080ff10e8e32","agent":{"id":"node-agent","name":"Node Agent","runtime":"node","capabilities":["node_execution"],"reasoning_enabled":false},"request_metadata":{}}}
# Subtest: UnifiedAgentAdapter forwards trusted admin execution context to node dispatch
ok 16 - UnifiedAgentAdapter forwards trusted admin execution context to node dispatch
  ---
  duration_ms: 268.941179
  ...
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [AUDIT] {"event":"agent_task_init","status":"PENDING","timestamp":"2026-06-01T16:31:49.037Z","taskId":"fd4671d2-dcd9-4dcf-a83b-5fce263e83e4","tenant_id":"tenant-1","actor_id":"user-1","agent_id":"node-agent","metadata":{"correlation_id":"650e44ef-baca-4ec4-ac9e-1113f9292740","task_id":"fd4671d2-dcd9-4dcf-a83b-5fce263e83e4","agent":{"id":"node-agent","name":"Node Agent","runtime":"node","capabilities":["node_execution"],"reasoning_enabled":false},"request_metadata":{}}}
# Subtest: UnifiedAgentAdapter logs EXECUTE_<TYPE>_WITHOUT_REASONING action when reasoning is disabled
ok 17 - UnifiedAgentAdapter logs EXECUTE_<TYPE>_WITHOUT_REASONING action when reasoning is disabled
  ---
  duration_ms: 212.028539
  ...
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [AUDIT] {"event":"agent_task_init","status":"PENDING","timestamp":"2026-06-01T16:31:49.270Z","taskId":"fe469711-6582-4363-b871-7ca8bc123d92","tenant_id":"tenant-1","actor_id":"user-1","agent_id":"node-agent","metadata":{"correlation_id":"2eaf3647-7be5-4ab0-aa70-d0e1c62f12d9","task_id":"fe469711-6582-4363-b871-7ca8bc123d92","agent":{"id":"node-agent","name":"Node Agent","runtime":"node","capabilities":["node_execution","reasoning"],"reasoning_enabled":true},"request_metadata":{}}}
# [INFO] 🧠 Agent [Node Agent] is reasoning about the legal task...
# Subtest: UnifiedAgentAdapter logs EXECUTE_<TYPE>_WITH_REASONING action when reasoning is enabled
ok 18 - UnifiedAgentAdapter logs EXECUTE_<TYPE>_WITH_REASONING action when reasoning is enabled
  ---
  duration_ms: 232.095227
  ...
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [AUDIT] {"event":"agent_task_init","status":"PENDING","timestamp":"2026-06-01T16:31:49.399Z","taskId":"dcdf9342-6aa2-4fd6-80cc-92a49e4f24b5","tenant_id":"tenant-1","actor_id":"user-1","agent_id":"node-agent","metadata":{"correlation_id":"9c53bf7e-653f-4d5d-a63c-bb969619237c","task_id":"dcdf9342-6aa2-4fd6-80cc-92a49e4f24b5","agent":{"id":"node-agent","name":"Node Agent","runtime":"node","capabilities":["node_execution"],"reasoning_enabled":false},"request_metadata":{"trace_id":"trace-err"}}}
# [ERROR] 💥 Intelligence Failure at Agent node-agent {
#   err: NodeExecutionDispatchError: RUNTIME_FAILURE: Node runtime execution failed for agent node-agent: provider crashed
#       at UnifiedAgentAdapter.mapNodeExecutionError (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509383.b7d4b3f604789.mjs:901:16)
#       at UnifiedAgentAdapter.executeNodeInternal (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509383.b7d4b3f604789.mjs:857:24)
#       at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509383.b7d4b3f604789.mjs:591:19)
#       ... 4 lines matching cause stack trace ...
#       at async Test.processPendingSubtests (node:internal/test_runner/test:526:7) {
#     code: 'RUNTIME_FAILURE',
#     classification: 'RUNTIME_FAILURE',
#     agentId: 'node-agent',
#     cause: Error: provider crashed
#         at runAgentStub (file:///workspace/swarms/tests/unifiedAgentAdapter.nodeDispatch.integration.test.js:512:19)
#         at UnifiedAgentAdapter.executeNodeInternal (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509383.b7d4b3f604789.mjs:848:26)
#         at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509383.b7d4b3f604789.mjs:591:19)
#         at async waitForActual (node:assert:533:5)
#         at async Function.rejects (node:assert:654:25)
#         at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.nodeDispatch.integration.test.js:556:3)
#         at async Test.run (node:internal/test_runner/test:797:9)
#         at async Test.processPendingSubtests (node:internal/test_runner/test:526:7) {
#       code: 'AGENT_EXECUTION_FAILED'
#     }
#   },
#   agentId: 'node-agent',
#   structuredFailure: { failure_class: 'RUNTIME_FAILURE', upstream_status: null },
#   normalizedError: {
#     message: 'RUNTIME_FAILURE: Node runtime execution failed for agent node-agent: provider crashed',
#     code: 'RUNTIME_FAILURE',
#     stack: 'NodeExecutionDispatchError: RUNTIME_FAILURE: Node runtime execution failed for agent node-agent: provider crashed\\n' +
#       '    at UnifiedAgentAdapter.mapNodeExecutionError (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509383.b7d4b3f604789.mjs:901:16)\\n' +
#       '    at UnifiedAgentAdapter.executeNodeInternal (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509383.b7d4b3f604789.mjs:857:24)\\n' +
#       '    at async UnifiedAgentAdapter.executeAgent (file://...[truncated]'
#   },
#   originalStack: 'NodeExecutionDispatchError: RUNTIME_FAILURE: Node runtime execution failed for agent node-agent: provider crashed\\n' +
#     '    at UnifiedAgentAdapter.mapNodeExecutionError (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509383.b7d4b3f604789.mjs:901:16)\\n' +
#     '    at UnifiedAgentAdapter.executeNodeInternal (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509383.b7d4b3f604789.mjs:857:24)\\n' +
#     '    at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509383.b7d4b3f604789.mjs:591:19)\\n' +
#     '    at async waitForActual (node:assert:533:5)\\n' +
#     '    at async Function.rejects (node:assert:654:25)\\n' +
#     '    at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.nodeDispatch.integration.test.js:556:3)\\n' +
#     '    at async Test.run (node:internal/test_runner/test:797:9)\\n' +
#     '    at async Test.processPendingSubtests (node:internal/test_runner/test:526:7)'
# }
# Subtest: UnifiedAgentAdapter marks task FAILED when node dispatch throws runtime failure
ok 19 - UnifiedAgentAdapter marks task FAILED when node dispatch throws runtime failure
  ---
  duration_ms: 133.526728
  ...
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [AUDIT] {"event":"agent_task_init","status":"PENDING","timestamp":"2026-06-01T16:31:49.566Z","taskId":"e0604b15-df1a-4c4a-bd8e-77d1ac43dcec","tenant_id":"tenant-1","actor_id":"user-1","agent_id":"node-agent","metadata":{"correlation_id":"eb38bfb2-dc7a-4a49-adba-fb9b8b1beab2","task_id":"e0604b15-df1a-4c4a-bd8e-77d1ac43dcec","agent":{"id":"node-agent","name":"Node Agent","runtime":"node","capabilities":["node_execution"],"reasoning_enabled":false},"request_metadata":{"trace_id":"node-agent-missing-runner"}}}
# [ERROR] 💥 Intelligence Failure at Agent node-agent {
#   err: NodeExecutionDispatchError: CONFIG_NOT_FOUND: Node dispatcher module missing for agent node-agent
#       at UnifiedAgentAdapter.mapNodeExecutionError (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509554.2dcaa9b6ec4a1.mjs:898:20)
#       at UnifiedAgentAdapter.executeNodeInternal (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509554.2dcaa9b6ec4a1.mjs:857:24)
#       at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509554.2dcaa9b6ec4a1.mjs:591:19)
#       at async waitForActual (node:assert:533:5)
#       at async Function.rejects (node:assert:654:25)
#       at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.nodeDispatch.integration.test.js:632:5)
#       at async Test.run (node:internal/test_runner/test:797:9)
#       at async Test.processPendingSubtests (node:internal/test_runner/test:526:7) {
#     code: 'CONFIG_NOT_FOUND',
#     classification: 'CONFIG_FAILURE',
#     agentId: 'node-agent',
#     cause: Error [ERR_MODULE_NOT_FOUND]: Cannot find module '/workspace/swarms/src/runners/agentRunner.js' imported from /workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509554.2dcaa9b6ec4a1.mjs
#         at finalizeResolution (node:internal/modules/esm/resolve:283:11)
#         at moduleResolve (node:internal/modules/esm/resolve:952:10)
#         at defaultResolve (node:internal/modules/esm/resolve:1188:11)
#         at ModuleLoader.defaultResolve (node:internal/modules/esm/loader:708:12)
#         at \#cachedDefaultResolve (node:internal/modules/esm/loader:657:25)
#         at ModuleLoader.resolve (node:internal/modules/esm/loader:640:38)
#         at ModuleLoader.getModuleJobForImport (node:internal/modules/esm/loader:264:38)
#         at ModuleLoader.import (node:internal/modules/esm/loader:605:34)
#         at defaultImportModuleDynamicallyForModule (node:internal/modules/esm/utils:221:31)
#         at importModuleDynamicallyCallback (node:internal/modules/esm/utils:260:12) {
#       code: 'ERR_MODULE_NOT_FOUND',
#       url: 'file:///workspace/swarms/src/runners/agentRunner.js'
#     }
#   },
#   agentId: 'node-agent',
#   structuredFailure: { failure_class: 'CONFIG_NOT_FOUND', upstream_status: null },
#   normalizedError: {
#     message: 'CONFIG_NOT_FOUND: Node dispatcher module missing for agent node-agent',
#     code: 'CONFIG_NOT_FOUND',
#     stack: 'NodeExecutionDispatchError: CONFIG_NOT_FOUND: Node dispatcher module missing for agent node-agent\\n' +
#       '    at UnifiedAgentAdapter.mapNodeExecutionError (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509554.2dcaa9b6ec4a1.mjs:898:20)\\n' +
#       '    at UnifiedAgentAdapter.executeNodeInternal (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509554.2dcaa9b6ec4a1.mjs:857:24)\\n' +
#       '    at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarm...[truncated]'
#   },
#   originalStack: 'NodeExecutionDispatchError: CONFIG_NOT_FOUND: Node dispatcher module missing for agent node-agent\\n' +
#     '    at UnifiedAgentAdapter.mapNodeExecutionError (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509554.2dcaa9b6ec4a1.mjs:898:20)\\n' +
#     '    at UnifiedAgentAdapter.executeNodeInternal (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509554.2dcaa9b6ec4a1.mjs:857:24)\\n' +
#     '    at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509554.2dcaa9b6ec4a1.mjs:591:19)\\n' +
#     '    at async waitForActual (node:assert:533:5)\\n' +
#     '    at async Function.rejects (node:assert:654:25)\\n' +
#     '    at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.nodeDispatch.integration.test.js:632:5)\\n' +
#     '    at async Test.run (node:internal/test_runner/test:797:9)\\n' +
#     '    at async Test.processPendingSubtests (node:internal/test_runner/test:526:7)'
# }
# [AUDIT] {"event":"agent_task_init","status":"PENDING","timestamp":"2026-06-01T16:31:49.573Z","taskId":"dfd91826-af43-483e-8b6f-b959bde69c06","tenant_id":"tenant-1","actor_id":"user-1","agent_id":"hybrid-agent","metadata":{"correlation_id":"46d03174-4870-4b93-b30d-e44ff98fbeea","task_id":"dfd91826-af43-483e-8b6f-b959bde69c06","agent":{"id":"hybrid-agent","name":"Hybrid Agent","runtime":"hybrid","capabilities":["node_execution"],"reasoning_enabled":false},"request_metadata":{"trace_id":"hybrid-agent-missing-runner"}}}
# [ERROR] 💥 Intelligence Failure at Agent hybrid-agent {
#   err: NodeExecutionDispatchError: CONFIG_NOT_FOUND: Node dispatcher module missing for agent hybrid-agent
#       at UnifiedAgentAdapter.mapNodeExecutionError (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509554.2dcaa9b6ec4a1.mjs:898:20)
#       at UnifiedAgentAdapter.executeNodeInternal (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509554.2dcaa9b6ec4a1.mjs:857:24)
#       at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509554.2dcaa9b6ec4a1.mjs:591:19)
#       at async waitForActual (node:assert:533:5)
#       at async Function.rejects (node:assert:654:25)
#       at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.nodeDispatch.integration.test.js:632:5)
#       at async Test.run (node:internal/test_runner/test:797:9)
#       at async Test.processPendingSubtests (node:internal/test_runner/test:526:7) {
#     code: 'CONFIG_NOT_FOUND',
#     classification: 'CONFIG_FAILURE',
#     agentId: 'hybrid-agent',
#     cause: Error [ERR_MODULE_NOT_FOUND]: Cannot find module '/workspace/swarms/src/runners/agentRunner.js' imported from /workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509554.2dcaa9b6ec4a1.mjs
#         at finalizeResolution (node:internal/modules/esm/resolve:283:11)
#         at moduleResolve (node:internal/modules/esm/resolve:952:10)
#         at defaultResolve (node:internal/modules/esm/resolve:1188:11)
#         at ModuleLoader.defaultResolve (node:internal/modules/esm/loader:708:12)
#         at \#cachedDefaultResolve (node:internal/modules/esm/loader:657:25)
#         at ModuleLoader.resolve (node:internal/modules/esm/loader:640:38)
#         at ModuleLoader.getModuleJobForImport (node:internal/modules/esm/loader:264:38)
#         at ModuleLoader.import (node:internal/modules/esm/loader:605:34)
#         at defaultImportModuleDynamicallyForModule (node:internal/modules/esm/utils:221:31)
#         at importModuleDynamicallyCallback (node:internal/modules/esm/utils:260:12) {
#       code: 'ERR_MODULE_NOT_FOUND',
#       url: 'file:///workspace/swarms/src/runners/agentRunner.js'
#     }
#   },
#   agentId: 'hybrid-agent',
#   structuredFailure: { failure_class: 'CONFIG_NOT_FOUND', upstream_status: null },
#   normalizedError: {
#     message: 'CONFIG_NOT_FOUND: Node dispatcher module missing for agent hybrid-agent',
#     code: 'CONFIG_NOT_FOUND',
#     stack: 'NodeExecutionDispatchError: CONFIG_NOT_FOUND: Node dispatcher module missing for agent hybrid-agent\\n' +
#       '    at UnifiedAgentAdapter.mapNodeExecutionError (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509554.2dcaa9b6ec4a1.mjs:898:20)\\n' +
#       '    at UnifiedAgentAdapter.executeNodeInternal (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509554.2dcaa9b6ec4a1.mjs:857:24)\\n' +
#       '    at async UnifiedAgentAdapter.executeAgent (file:///workspace/swa...[truncated]'
#   },
#   originalStack: 'NodeExecutionDispatchError: CONFIG_NOT_FOUND: Node dispatcher module missing for agent hybrid-agent\\n' +
#     '    at UnifiedAgentAdapter.mapNodeExecutionError (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509554.2dcaa9b6ec4a1.mjs:898:20)\\n' +
#     '    at UnifiedAgentAdapter.executeNodeInternal (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509554.2dcaa9b6ec4a1.mjs:857:24)\\n' +
#     '    at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509554.2dcaa9b6ec4a1.mjs:591:19)\\n' +
#     '    at async waitForActual (node:assert:533:5)\\n' +
#     '    at async Function.rejects (node:assert:654:25)\\n' +
#     '    at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.nodeDispatch.integration.test.js:632:5)\\n' +
#     '    at async Test.run (node:internal/test_runner/test:797:9)\\n' +
#     '    at async Test.processPendingSubtests (node:internal/test_runner/test:526:7)'
# }
# Subtest: UnifiedAgentAdapter reports CONFIG_NOT_FOUND when node dispatcher module is unavailable
ok 20 - UnifiedAgentAdapter reports CONFIG_NOT_FOUND when node dispatcher module is unavailable
  ---
  duration_ms: 169.994226
  ...
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [ERROR] 💥 Intelligence Failure at Agent node-agent {
#   err: 'unexpected string thrown from dispatcher',
#   agentId: 'node-agent',
#   structuredFailure: { failure_class: 'UNVERIFIED_RUNTIME', upstream_status: null },
#   normalizedError: { message: 'unexpected string thrown from dispatcher' }
# }
# Subtest: UnifiedAgentAdapter preserves thrown string message in audit on node dispatch
ok 21 - UnifiedAgentAdapter preserves thrown string message in audit on node dispatch
  ---
  duration_ms: 123.542233
  ...
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [AUDIT] {"event":"agent_task_init","status":"PENDING","timestamp":"2026-06-01T16:31:49.803Z","taskId":"d0c60905-2adc-4a5a-879a-34b737312a2a","tenant_id":"tenant-1","actor_id":"user-1","agent_id":"node-agent","metadata":{"correlation_id":"c5ae0e6c-c506-41d2-9d8e-b84b30afd095","task_id":"d0c60905-2adc-4a5a-879a-34b737312a2a","agent":{"id":"node-agent","name":"Node Agent","runtime":"node","capabilities":["node_execution"],"reasoning_enabled":false},"request_metadata":{"trace_id":"node-agent-missing-transitive"}}}
# [ERROR] 💥 Intelligence Failure at Agent node-agent {
#   err: NodeExecutionDispatchError: RUNTIME_FAILURE: Node runtime execution failed for agent node-agent: Cannot find package 'left-pad' imported from /workspace/src/runners/agentRunner.js
#       at UnifiedAgentAdapter.mapNodeExecutionError (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509791.d6d390de725f4.mjs:901:16)
#       at UnifiedAgentAdapter.executeNodeInternal (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509791.d6d390de725f4.mjs:857:24)
#       at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509791.d6d390de725f4.mjs:591:19)
#       at async waitForActual (node:assert:533:5)
#       ... 3 lines matching cause stack trace ...
#       at async Test.processPendingSubtests (node:internal/test_runner/test:526:7) {
#     code: 'RUNTIME_FAILURE',
#     classification: 'RUNTIME_FAILURE',
#     agentId: 'node-agent',
#     cause: Error: Cannot find package 'left-pad' imported from /workspace/src/runners/agentRunner.js
#         at adapter.getNodeDispatcher (file:///workspace/swarms/tests/unifiedAgentAdapter.nodeDispatch.integration.test.js:733:19)
#         at UnifiedAgentAdapter.executeNodeInternal (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509791.d6d390de725f4.mjs:847:41)
#         at UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509791.d6d390de725f4.mjs:591:30)
#         at async waitForActual (node:assert:533:5)
#         at async Function.rejects (node:assert:654:25)
#         at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.nodeDispatch.integration.test.js:751:3)
#         at async Test.run (node:internal/test_runner/test:797:9)
#         at async Test.processPendingSubtests (node:internal/test_runner/test:526:7) {
#       code: 'ERR_MODULE_NOT_FOUND'
#     }
#   },
#   agentId: 'node-agent',
#   structuredFailure: { failure_class: 'RUNTIME_FAILURE', upstream_status: null },
#   normalizedError: {
#     message: "RUNTIME_FAILURE: Node runtime execution failed for agent node-agent: Cannot find package 'left-pad' imported from /workspace/src/runners/agentRunner.js",
#     code: 'RUNTIME_FAILURE',
#     stack: "NodeExecutionDispatchError: RUNTIME_FAILURE: Node runtime execution failed for agent node-agent: Cannot find package 'left-pad' imported from /workspace/src/runners/agentRunner.js\\n" +
#       '    at UnifiedAgentAdapter.mapNodeExecutionError (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509791.d6d390de725f4.mjs:901:16)\\n' +
#       '    at UnifiedAgentAdapter.executeNodeInternal (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509791.d6d390de725f4....[truncated]'
#   },
#   originalStack: "NodeExecutionDispatchError: RUNTIME_FAILURE: Node runtime execution failed for agent node-agent: Cannot find package 'left-pad' imported from /workspace/src/runners/agentRunner.js\\n" +
#     '    at UnifiedAgentAdapter.mapNodeExecutionError (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509791.d6d390de725f4.mjs:901:16)\\n' +
#     '    at UnifiedAgentAdapter.executeNodeInternal (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509791.d6d390de725f4.mjs:857:24)\\n' +
#     '    at async UnifiedAgentAdapter.executeAgent (file:///workspace/swarms/src/services/unifiedAgentAdapter.node-dispatch.7270.1780331509791.d6d390de725f4.mjs:591:19)\\n' +
#     '    at async waitForActual (node:assert:533:5)\\n' +
#     '    at async Function.rejects (node:assert:654:25)\\n' +
#     '    at async TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.nodeDispatch.integration.test.js:751:3)\\n' +
#     '    at async Test.run (node:internal/test_runner/test:797:9)\\n' +
#     '    at async Test.processPendingSubtests (node:internal/test_runner/test:526:7)'
# }
# Subtest: UnifiedAgentAdapter keeps transitive ERR_MODULE_NOT_FOUND as runtime failure
ok 22 - UnifiedAgentAdapter keeps transitive ERR_MODULE_NOT_FOUND as runtime failure
  ---
  duration_ms: 106.840726
  ...
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 0,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [AUDIT] {"event":"agent_task_init","status":"PENDING","timestamp":"2026-06-01T16:31:49.925Z","taskId":"144ef3bb-35a5-497a-abf2-474dd68c98b3","tenant_id":"tenant-1","actor_id":"user-1","agent_id":"reasoning-node-agent","metadata":{"correlation_id":"0fd0b505-a97b-4b92-b276-d40344b4d98f","task_id":"144ef3bb-35a5-497a-abf2-474dd68c98b3","agent":{"id":"reasoning-node-agent","name":"Reasoning Node Agent","runtime":"node","capabilities":["node_execution","reasoning"],"reasoning_enabled":true},"request_metadata":{"trace_id":"trace-reasoning"}}}
# [INFO] 🧠 Agent [Reasoning Node Agent] is reasoning about the legal task...
# Subtest: UnifiedAgentAdapter reasoning path stores execution plan in payload.context and applies optional hook
ok 23 - UnifiedAgentAdapter reasoning path stores execution plan in payload.context and applies optional hook
  ---
  duration_ms: 120.233429
  ...
# Subtest: forwardToPythonEngine guards missing PYTHON_BACKEND_URL with CONFIG_NOT_FOUND and structured log
ok 24 - forwardToPythonEngine guards missing PYTHON_BACKEND_URL with CONFIG_NOT_FOUND and structured log
  ---
  duration_ms: 14.018239
  ...
# Subtest: loadRegistry logs loaded and reasoning-enabled counters for mixed definitions
ok 25 - loadRegistry logs loaded and reasoning-enabled counters for mixed definitions
  ---
  duration_ms: 1.664583
  ...
# Subtest: loadRegistry supports primary and fallback registry paths and accepts dict-keyed agents
ok 26 - loadRegistry supports primary and fallback registry paths and accepts dict-keyed agents
  ---
  duration_ms: 1.835763
  ...
# Subtest: node dispatcher CONFIG_NOT_FOUND is limited to the canonical agentRunner module
ok 27 - node dispatcher CONFIG_NOT_FOUND is limited to the canonical agentRunner module
  ---
  duration_ms: 1.440501
  ...
# [INFO] Registry startup integrity check {
#   registryPathSource: 'default',
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] ✅ LexPrim Intelligence Matrix loaded {
#   loadedAgents: 2,
#   reasoningEnabledAgents: 0,
#   registryPath: '/workspace/swarms/.agents/config/agents.yaml'
# }
# [INFO] Registry startup integrity check {
#   registryPathSource: 'env',
#   registryPath: '/tmp/registry-test-ryJAUy/registry.yaml'
# }
# [ERROR] ❌ Registry Integrity Breach {
#   err: RegistryStartupError: REGISTRY_LOAD_FAILURE: Invalid agent entry at index 0 (expected object)
#       at UnifiedAgentAdapter.loadRegistry (file:///workspace/swarms/src/services/unifiedAgentAdapter.js:356:31)
#       at new UnifiedAgentAdapter (file:///workspace/swarms/src/services/unifiedAgentAdapter.js:325:14)
#       at file:///workspace/swarms/tests/unifiedAgentAdapter.test.js:106:11
#       at getActual (node:assert:498:5)
#       at Function.throws (node:assert:644:24)
#       at TestContext.<anonymous> (file:///workspace/swarms/tests/unifiedAgentAdapter.test.js:105:10)
#       at async Test.run (node:internal/test_runner/test:797:9)
#       at async Test.processPendingSubtests (node:internal/test_runner/test:526:7) {
#     code: 'REGISTRY_LOAD_FAILURE',
#     registryPath: '/tmp/registry-test-ryJAUy/registry.yaml'
#   },
#   registryPath: '/tmp/registry-test-ryJAUy/registry.yaml',
#   failurePhase: 'schema_or_io',
#   failureCode: 'REGISTRY_LOAD_FAILURE'
# }
# Subtest: loadRegistry runtime: invalid array entries trigger startup failure and unhealthy service
ok 28 - loadRegistry runtime: invalid array entries trigger startup failure and unhealthy service
  ---
  duration_ms: 90.81951
  ...
# Subtest: loadRegistry array path validates schema and fails fast instead of skipping entries
ok 29 - loadRegistry array path validates schema and fails fast instead of skipping entries
  ---
  duration_ms: 1.08772
  ...
# Subtest: live .agents/config/agents.yaml declares mihwar/bayyinah and matches Modal deployment
ok 30 - live .agents/config/agents.yaml declares mihwar/bayyinah and matches Modal deployment
  ---
  duration_ms: 1.120016
  ...
1..30
# tests 30
# suites 0
# pass 30
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 6295.366658

[exit status: 0]
```

### 5. ADR-0001 boundary gate

```text
$ bash scripts/commander/adr-0001-boundary-gate.sh .
[INFO] ADR-0001 boundary gate
[INFO] repo=/workspace/swarms
[OK]   no autoStart activation flag detected
[RESULT] PASS

[exit status: 0]
```

### 6. Modal boundary gate

```text
$ bash scripts/commander/modal-boundary-gate.sh .
[INFO] Modal boundary gate
[INFO] repo=/workspace/swarms
[OK]   no *.modal.run reference in src,public
[OK]   no Modal SDK import found in client surfaces
[OK]   server-side relay present (.agents/pr_review.py)
[OK]   package init present: .agents/router/__init__.py
[OK]   package init present: .agents/validators/__init__.py
[WARN] SECRET_MISSING: BAYYINAH_ENDPOINT (expected outside CI/runtime)
[WARN] SECRET_MISSING: MIHWAR_ENDPOINT (expected outside CI/runtime)
[WARN] SECRET_MISSING: endpoint-specific runtime token (expected outside CI/runtime)
[OK]   workflow .github/workflows/agent-review.yml has no hardcoded modal URL
[INFO] ADR-0001 boundary gate
[INFO] repo=/workspace/swarms
[OK]   no autoStart activation flag detected
[RESULT] PASS
[OK]   ADR-0001 boundary gate passed
[WARN] no build artifact directories to scan (skipped)
[RESULT] PASS

[exit status: 0]
```

### 7. Repository secret scan gate

```text
$ python3 scripts/security/static_audit.py .
No obvious secrets found.

[exit status: 0]
```
