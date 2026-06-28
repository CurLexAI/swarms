# Repository Dependency Graph Analysis

Root: `swarms`  ·  analysis is read-only, stdlib-only.

## Python dependency graph

- Nodes (files): **98**
- Edges (import relations): **89**
- Weakly connected components: **40**
- Circular dependencies detected: **0**

### Most central modules (degree centrality)

| Module | In (imported by) | Out (imports) | Total |
|---|---|---|---|
| `tests/_agents_loader.py` | 12 | 1 | 13 |
| `.agents/providers/types.py` | 12 | 0 | 12 |
| `src/policy/sovereign/audited_router.py` | 6 | 2 | 8 |
| `sama_ingestion_swarm/agent_parser.py` | 3 | 4 | 7 |
| `.agents/providers/__init__.py` | 0 | 7 | 7 |
| `.agents/router/types.py` | 6 | 0 | 6 |
| `src/policy/sovereign/model_router.py` | 2 | 4 | 6 |
| `sama_ingestion_swarm/orchestrator.py` | 1 | 5 | 6 |
| `tests/test_full_pipeline.py` | 0 | 6 | 6 |
| `sama_ingestion_swarm/__init__.py` | 4 | 1 | 5 |
| `sama_ingestion_swarm/agent_fetcher.py` | 3 | 2 | 5 |
| `sama_ingestion_swarm/agent_auditor.py` | 2 | 3 | 5 |

### Circular dependencies (DFS cycle detection)

None found — the dependency graph is a DAG.

### Build / load order (topological sort)

Acyclic. First 20 in valid dependency-first order:
  - `.agents/adapters/lexprim_bridge.py`
  - `.agents/drive_service_agent.py`
  - `.agents/gateway/mcp_server.py`
  - `.agents/invoke.py`
  - `.agents/mcp/aegis_gateway.py`
  - `.agents/mcp/qarar_api_server.py`
  - `.agents/pr_review.py`
  - `.agents/providers/types.py`
  - `.agents/router/__init__.py`
  - `.agents/router/types.py`
  - `.agents/runtime_security.py`
  - `.agents/validate.py`
  - `.agents/validators/qala_audit_sink.py`
  - `.agents/validators/qala_ksa_pii.py`
  - `.agents/validators/qala_trace.py`
  - `.agents/validators/sovereign_security_controls.py`
  - `modal/qarar_rag_infra.py`
  - `qarar-swarms-sovereign-integration/overlay/integrations/python/qarar_swarms/adapter.py`
  - `scripts/analysis/repo_graph_analysis.py`
  - `scripts/check-secrets-manifest.py`

### Isolated / orphaned files (connected components)

Files with **no** intra-repo import edges (in or out):
  - `.agents/drive_service_agent.py`
  - `.agents/gateway/mcp_server.py`
  - `.agents/invoke.py`
  - `.agents/mcp/qarar_api_server.py`
  - `.agents/router/__init__.py`
  - `.agents/validate.py`
  - `.agents/validators/sovereign_security_controls.py`
  - `modal/qarar_rag_infra.py`
  - `scripts/analysis/repo_graph_analysis.py`
  - `scripts/check-secrets-manifest.py`
  - `scripts/commander/copilot-agent-profiles-gate.py`
  - `scripts/commander/swarm-presence-monitor.py`
  - `scripts/hf_public_coding_smoke.py`
  - `scripts/security/runtime_policy_audit.py`
  - `scripts/security/static_audit.py`
  - `scripts/sign_request.py`
  - `scripts/verify_aegis.py`
  - `sovereign_network_agent_systemd_v1/network_health_guard.py`
  - `src/__init__.py`
  - `src/agents/__init__.py`
  - `src/policy/sovereign/__init__.py`
  - `src/policy/sovereign/providers/__init__.py`
  - `tests/test_adr_0001_boundary_gate.py`
  - `tests/test_gateway_stub.py`
  - `tests/test_integration_workflow_gates.py`
  - `tests/test_integrations_control_plane_gates.py`
  - `tests/test_modal_activation_tooling.py`
  - `tests/test_modal_boundary_gate.py`
  - `tests/test_qala_egress_residency_gate.py`
  - `tests/test_sovereign_security_controls.py`

Small detached clusters (2–3 files, weakly connected to nothing else):
  - `.agents/ingest_test.py`, `.agents/modal_app.py`, `.agents/runtime_security.py`
  - `.agents/mcp/aegis_gateway.py`, `.agents/mcp/server.py`, `.agents/mcp/server_offline.py`
  - `.agents/adapters/lexprim_bridge.py`, `.agents/adapters/lexprim_bridge_test.py`
  - `.agents/pr_review.py`, `tests/test_pr_review_modal_relay.py`
  - `scripts/command_center_archiver.py`, `tests/test_command_center_archiver.py`
  - `src/agents/security_agent.py`, `tests/test_qarar_security_agent.py`

### Dependency fan-out (BFS traversal)

From `.agents/providers/__init__.py`:
  - depth 1: `.agents/providers/anthropic_provider.py`, `.agents/providers/huggingface_provider.py`, `.agents/providers/local_llama_cpp.py`, `.agents/providers/local_ollama.py`, `.agents/providers/modal_provider.py`, `.agents/providers/openai_provider.py`, `.agents/providers/types.py`

From `tests/test_full_pipeline.py`:
  - depth 1: `src/policy/sovereign/audited_router.py`, `src/policy/sovereign/classification.py`, `src/policy/sovereign/model_router.py`, `src/policy/sovereign/provider_interface.py`, `src/policy/sovereign/providers/local_llama_cpp.py`, `src/policy/sovereign/providers/local_ollama.py`

## TypeScript/JavaScript dependency graph

- Nodes (files): **100**
- Edges (import relations): **72**
- Weakly connected components: **49**
- Circular dependencies detected: **0**

### Most central modules (degree centrality)

| Module | In (imported by) | Out (imports) | Total |
|---|---|---|---|
| `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/swarms/sovereign-swarms-contract.ts` | 4 | 3 | 7 |
| `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/swarms/qarar-sovereign-client.ts` | 2 | 5 | 7 |
| `sovereign-connectivity-poc/packages/shared/src/index.js` | 6 | 0 | 6 |
| `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/swarms/protocol-adapter.ts` | 2 | 3 | 5 |
| `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/swarms/tool-adapter.ts` | 1 | 4 | 5 |
| `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/swarms/index.ts` | 1 | 4 | 5 |
| `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/core/result.ts` | 4 | 0 | 4 |
| `src/policy/runtime-policy.ts` | 4 | 0 | 4 |
| `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/contracts/data-classification.ts` | 4 | 0 | 4 |
| `.agents/mcp/modal-mcp/src/server.ts` | 0 | 4 | 4 |
| `src/utils/auditLogger.js` | 3 | 0 | 3 |
| `.agents/mcp/modal-mcp/src/types.ts` | 3 | 0 | 3 |

### Circular dependencies (DFS cycle detection)

None found — the dependency graph is a DAG.

### Build / load order (topological sort)

Acyclic. First 20 in valid dependency-first order:
  - `.agents/mcp/cloudflare-mcp/src/modal-client.ts`
  - `.agents/mcp/cloudflare-mcp/src/workers-oauth-utils.ts`
  - `.agents/mcp/modal-mcp/src/policyGate.ts`
  - `.agents/mcp/modal-mcp/src/types.ts`
  - `dev-factory/src/healthcheck.mjs`
  - `public/trust/vendor/fallback-lib.js`
  - `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/audit/append-only-file-sink.ts`
  - `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/contracts/data-classification.ts`
  - `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/contracts/sovereign-output.ts`
  - `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/core/result.ts`
  - `scripts/check-cdn-sri.mjs`
  - `scripts/check-service-divergence.mjs`
  - `scripts/check-supabase-public-boundary.mjs`
  - `scripts/dev-cli-doctor.mjs`
  - `scripts/generate-frontend-integrity.mjs`
  - `scripts/validate-launch-evidence.mjs`
  - `sovereign-connectivity-poc/apps/api/src/server.d.ts`
  - `sovereign-connectivity-poc/apps/windows-agent/src/cli.d.ts`
  - `sovereign-connectivity-poc/packages/policy/src/index.js`
  - `sovereign-connectivity-poc/packages/shared/src/index.d.ts`

### Isolated / orphaned files (connected components)

Files with **no** intra-repo import edges (in or out):
  - `dev-factory/src/healthcheck.mjs`
  - `public/trust/vendor/fallback-lib.js`
  - `scripts/check-cdn-sri.mjs`
  - `scripts/check-service-divergence.mjs`
  - `scripts/check-supabase-public-boundary.mjs`
  - `scripts/dev-cli-doctor.mjs`
  - `scripts/generate-frontend-integrity.mjs`
  - `scripts/validate-launch-evidence.mjs`
  - `sovereign-connectivity-poc/apps/api/src/server.d.ts`
  - `sovereign-connectivity-poc/apps/windows-agent/src/cli.d.ts`
  - `sovereign-connectivity-poc/packages/shared/src/index.d.ts`
  - `sovereign-connectivity-poc/vitest.config.ts`
  - `src/backend/chatApi.ts`
  - `src/ports/quicknodeRpcPort.ts`
  - `src/runners/agentRunner.d.ts`
  - `src/security/qalaAuditSink.ts`
  - `src/security/qalaKsaPii.ts`
  - `src/security/qalaTrace.ts`
  - `src/security/sovereignCyberRadar.js`
  - `src/security/sovereignCyberRadar.ts`
  - `src/services/huggingface.ts`
  - `src/services/unifiedAgentAdapterErrorUtils.d.ts`
  - `src/utils/auditLogger.d.ts`
  - `src/utils/logger.d.ts`
  - `tests/auditService.lifecycleSeq.test.js`
  - `tests/cdn-sri-validation.test.js`
  - `tests/controlPlaneSecurityService.test.js`
  - `tests/huggingFaceBoundary.test.js`
  - `tests/modalMcpPolicyGate.test.js`
  - `tests/sovereignCyberRadar.test.js`
  - `tests/unifiedAgentAdapter.executeAgent.non2xx.integration.test.js`
  - `tests/unifiedAgentAdapter.nodeDispatch.integration.test.js`
  - `tests/unifiedAgentAdapter.test.js`

Small detached clusters (2–3 files, weakly connected to nothing else):
  - `src/backend/chatApi.js`, `tests/chatApi.test.js`
  - `src/models/modelRegistry.ts`, `tests/modelRegistry.test.ts`
  - `src/ports/quicknodeRpcPort.js`, `tests/quicknodeBoundary.test.js`
  - `src/runners/clientAgentRelay.ts`, `tests/clientModalBoundary.e2e.test.js`
  - `src/security/bayyinahRedactor.ts`, `tests/bayyinahRedactor.test.ts`
  - `src/security/contentSecurityPolicy.ts`, `tests/contentSecurityPolicy.test.js`
  - `src/security/qalaAuditSink.js`, `tests/qalaAuditSink.test.js`
  - `src/security/qalaKsaPii.js`, `tests/qalaKsaPii.test.js`
  - `src/security/qalaTrace.js`, `tests/qalaTrace.test.js`
  - `src/services/agentRelayService.ts`, `tests/agentRelayService.test.js`

### Dependency fan-out (BFS traversal)

From `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/swarms/qarar-sovereign-client.ts`:
  - depth 1: `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/audit/append-only-file-sink.ts`, `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/contracts/sovereign-output.ts`, `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/core/result.ts`, `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/swarms/protocol-adapter.ts`, `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/swarms/sovereign-swarms-contract.ts`
  - depth 2: `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/security/egress-policy.ts`, `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/contracts/data-classification.ts`

From `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/swarms/tool-adapter.ts`:
  - depth 1: `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/contracts/data-classification.ts`, `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/core/result.ts`, `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/swarms/qarar-sovereign-client.ts`, `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/swarms/sovereign-swarms-contract.ts`
  - depth 2: `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/audit/append-only-file-sink.ts`, `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/contracts/sovereign-output.ts`, `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/swarms/protocol-adapter.ts`
  - depth 3: `qarar-swarms-sovereign-integration/overlay/qarar/packages/bayyinah/src/security/egress-policy.ts`

