# Security Policy

## Scope

This policy applies to all code, workflows, and operational assets in `CurLexAI/swarms`.

## Reporting a Vulnerability

Please report vulnerabilities privately to:

- **Email:** `security@curlex.ai`

Include:
- Affected component/file
- Reproduction steps or proof of concept
- Impact assessment
- Suggested mitigation (if known)

## Response Targets

- Initial triage acknowledgement: within 72 hours
- Severity classification and remediation plan: as soon as triage is complete

## Handling Rules

- Do not disclose vulnerabilities publicly before coordinated remediation.
- Do not include secrets in reports, tickets, or pull requests.
- Use sanitized logs and redacted payloads.

## Security Baselines

- mTLS for service-to-service channels
- Input validation on external boundaries
- No hard-coded secrets
- Principle of least privilege for tokens and runtime roles

## Compliance Notes

Where applicable, implementation should align with organizational requirements (including NCA ECC/CSCC and PDPL handling expectations), and must be backed by evidence before any compliance claim is made.
