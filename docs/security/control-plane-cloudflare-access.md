# Control Plane Access Enforcement Mapping

Status: CHANGED BUT NOT VERIFIED

## Cloudflare Zero Trust control-path baseline

1. Create a dedicated Cloudflare Access application for `/enterprise/control` (or the runtime-equivalent `/control` route if it is the externally routed path).
2. Enforce identity policy with explicit MFA requirement (IdP auth + device/session posture), not application-only checks.
3. Remove legacy Basic Auth middleware or gateway rules on the same path to avoid parallel authentication paths.
4. Forward Cloudflare Access JWT assertion to backend (`Cf-Access-Jwt-Assertion`) and reject unauthenticated control-plane calls.

## Backend mapping to `ControlPlaneSecurityService`

| Edge policy (Cloudflare Access) | Backend guard (`ControlPlaneSecurityService`) | Failure mode |
|---|---|---|
| Access app bound to control path | `getControlAuthPath()` exposes canonical `/enterprise/control` path for route binding. | `UNVERIFIED` if edge app is not mapped to this path. |
| Access JWT required on every request | `enforceCloudflareAccess()` checks `cf-access-jwt-assertion` header. | `AUTH_MISSING` |
| Trusted issuer only | `enforceCloudflareAccess()` validates `claims.iss` against `CF_ACCESS_TRUSTED_ISSUERS` when configured. | `AUTH_INVALID` |
| MFA required in Access policy | `enforceCloudflareAccess()` requires MFA evidence in `amr` or `acr` claims. | `AUTH_INVALID` |
| Enterprise SSO + app RBAC | `enforceEnterpriseAuth()` and `authorizeAction()` enforce protocol and least privilege. | `AUTH_INVALID` |

## Verification matrix

- Negative: request without Access token -> denied (`AUTH_MISSING`).
- Negative: request with token but no MFA claim -> denied (`AUTH_INVALID`).
- Positive: request with token + trusted issuer + MFA claim -> allowed by Cloudflare-access gate.

Repository tests currently assert source-level enforcement semantics; full runtime verification against a live Cloudflare tenant remains `UNVERIFIED_RUNTIME`.
