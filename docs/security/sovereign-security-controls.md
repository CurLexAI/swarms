# Qarar/Mihwar Sovereign Security Controls Registry

- **Status:** Architecture only — no runtime activation.
- **Decision date:** 2026-06-02.
- **Evidence label:** VERIFIED for repository artifacts only.
- **Compliance note:** ECC-2:2024 references are `UNVERIFIED_MAPPING` traceability entries, not verified regulatory compliance claims.

## Purpose

This document records the offline governance implementation for the eight proposed security controls around the Qarar/Mihwar operations boundary. The machine-readable registry is stored at `.agents/config/sovereign_security_controls.json`, and the deterministic validator is stored at `.agents/validators/sovereign_security_controls.py`.

The registry is intentionally non-deploying. It contains no secrets, no live endpoint URLs, no Docker activation, no Modal/Render calls, and no Wazuh, Suricata, Vault, Tailscale, ModSecurity, Nginx, or ClamAV runtime configuration.

## Zero-Trust for Agents

Every agent, service, device, and network path is treated as untrusted until it is authenticated, authorized, inspected, and logged. Automated response remains draft-only until the Qarar Decision Engine authorizes an action, and destructive or business-impacting actions require human review.

## Control Coverage

| Category | Registry ID | Intended role | Activation state |
|---|---|---|---|
| AV | `av-clamav` | Scan externally sourced documents before object-store ingestion. | `not_active` |
| EDR | `edr-wazuh-agent` | Monitor workload behavior and suspicious process, file, and network activity. | `not_active` |
| SIEM | `siem-wazuh-elastic` | Aggregate security events and preserve audit evidence for review. | `not_active` |
| IDS/IPS | `idsips-suricata` | Inspect internal container traffic for known attack patterns. | `not_active` |
| DLP | `dlp-custom-scanner` | Detect secrets and KSA PII before user output or model egress. | `not_active` |
| WAF | `waf-modsecurity-nginx` | Protect public API entry points from OWASP Top 10 request patterns. | `not_active` |
| NAC | `nac-tailscale` | Restrict operator and device access to approved identities and posture. | `not_active` |
| mTLS | `mtls-vault-pki` | Issue short-lived service certificates for mutual authentication. | `not_active` |

## Offline Guardrails

The validator enforces the following controls:

1. The registry must contain exactly the eight expected categories.
2. Each control must include integration points, least-privilege permissions, audit events, ECC traceability mappings, and an inactive deployment surface.
3. Metadata must remain `architecture_only` and `not_active`.
4. Registry constraints must prohibit runtime activation, external endpoints, and secret values.
5. ECC entries must use `UNVERIFIED_MAPPING` and must not claim verified compliance.
6. SOAR playbooks must include `qarar_decision_required`.
7. Secret-like strings and live endpoint URLs are rejected.

## Validation

Run the local validator:

```bash
python3 .agents/validators/sovereign_security_controls.py
```

Run the unit tests:

```bash
python3 -m pytest -q tests/test_sovereign_security_controls.py
```

## Design Decision

The implementation uses a JSON registry plus a deterministic Python validator rather than deployment manifests. This keeps the change inside the swarms agent-operations boundary and prevents accidental activation of external security tooling without operator-approved secrets, runtime topology, and human review.

## Layer Impact

- **Device Layer:** NAC and mTLS entries define intended posture and identity checks, but do not enroll devices or push MDM profiles.
- **Control Layer:** The registry gives Qarar/Mihwar a reviewable policy source, but does not change live control-plane behavior.
- **Connectivity Layer:** Tailscale/private-network concepts remain architecture-only and do not modify network routes.
- **Decision Layer:** SOAR playbooks are gated by Qarar decisions and human review for destructive actions.
