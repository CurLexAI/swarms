# Architecture Directive

Core: Bayyinah (knowledge/evidence SSOT, Qdrant) · Mihwar (control/security/compliance) · Qarar (public face).
Rules: every decision retrieves from Bayyinah; writes to Bayyinah only via Mihwar gate; Qarar never touches Bayyinah directly; all output carries provenance. Plan->Review(Mihwar)->Test(sandbox)->Approve->Deploy. All entities logged in Mihwar; unregistered = disabled. NCA ECC-2:2024 + PDPL gates.
