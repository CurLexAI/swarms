# Remediation Overlay Plan

- PR A: Documentation and systemd-safe network guard service.
- PR B: Scaffold target remains `qarar/packages/bayyinah/`.
- PR C: Safe additive overlay only after repository boundary review.

Status: PREPARE_PATCH_PLAN_ONLY

Constraints:
- Do not set `QARAR_NETWORK_DRY_RUN=false` without direct explicit approval.
- Do not reboot routers without `QARAR_ENABLE_ROUTER_REBOOT=true` and `QARAR_ROUTER_REBOOT_COMMAND`.
- Preserve all audit logs.
