> **CONFIDENTIAL — INTERNAL IP WORK PRODUCT**
> This audit is for internal verification planning and SAIP preparation only.
> Do not copy patent claim details into public-facing surfaces, marketing pages, or external prompts.

## PAT-001 — Bayyinah Truth Verification Engine — TruthGate + AuditTrail + LLM Bridge
- claim_summary: محرك تحقق حقائق يربط بوابة تحقق مع سجل تدقيق وجسر LLM لإنتاج مخرجات قابلة للمراجعة.
- code_evidence: src/services/ControlPlaneSecurityService.ts:32-39,137-162
- test_evidence: tests/controlPlaneSecurityService.test.js:8-25 + passing
- runtime_evidence: NOT VERIFIED
- actual_status: MEDIUM
- gap_description: لا يوجد دليل صريح على TruthGate أو LLM Bridge باسم/تنفيذ مكافئ؛ الموجود المثبت هو AuditTrail فقط.

## PAT-002 — BFT Multi-Agent Consensus — 5 agents (Muthabbit, Musnad, Muqin, Muhaqqiq, Muraji), 3-of-5 protocol, multiplicative confidence
- claim_summary: بروتوكول إجماع BFT بخمسة وكلاء مع عتبة 3/5 وثقة مضاعِفة للوصول لحكم نهائي.
- code_evidence: NO EVIDENCE FOUND
- test_evidence: NO TEST FOUND
- runtime_evidence: NOT VERIFIED
- actual_status: MISSING
- gap_description: لا يوجد تنفيذ بالأسماء الخمسة أو منطق 3-of-5 أو multiplicative confidence داخل هذا المستودع.

## PAT-003 — Sovereign-First Model Routing — DATA_CLASSIFICATION enum, selectProviderByClassification(), permanently-blocked providers
- claim_summary: توجيه مزوّد النماذج حسب تصنيف البيانات مع حجب دائم لمزوّدين غير مسموحين.
- code_evidence: .agents/router/model_policy_engine.py:12-56
- test_evidence: NO TEST FOUND
- runtime_evidence: NOT VERIFIED
- actual_status: WEAK
- gap_description: يوجد routing policy عام، لكن لا يوجد DATA_CLASSIFICATION enum ولا selectProviderByClassification() ولا قائمة permanently-blocked providers كما صيغت المطالبة.

## PAT-004 — Cascaded ML Security Gate — CodeBERT + ModernBERT prompt-injection + BERT-small PII, <200ms CPU cascade, SAFE/WARNING/BLOCKED output
- claim_summary: بوابة أمنية متسلسلة تعتمد عدة نماذج ML متخصصة وتصدر SAFE/WARNING/BLOCKED بميزانية زمنية CPU أقل من 200ms.
- code_evidence: .agents/validators/qala_input_gate.py:34-56,120-180
- test_evidence: tests/test_qala_input_gate.py:71-113 + passing
- runtime_evidence: NOT VERIFIED
- actual_status: WEAK
- gap_description: الموجود rule-based gate وليس cascade لنماذج CodeBERT/ModernBERT/BERT-small، ولا يوجد إثبات SLA <200ms أو verdict WARNING (المستخدم BLOCKED/REQUEST_CHANGES/APPROVE).

## PAT-005 — Sector Factory — YAML-driven sector deployment, up to 50 agents per sector
- claim_summary: مصنع قطاعات يعتمد YAML لنشر قطاعات متعددة مع قدرة حتى 50 وكيل لكل قطاع.
- code_evidence: NO EVIDENCE FOUND
- test_evidence: NO TEST FOUND
- runtime_evidence: NOT VERIFIED
- actual_status: MISSING
- gap_description: OUT OF SCOPE: in LexPrim/Qarar monorepo per documented expected paths, وليس ضمن swarms الحالي.

## PAT-006 — Mihwar Multi-Swarm Orchestration — MihwarRouter + SwarmOrchestrator, 9 swarms, domain-based routing
- claim_summary: تنسيق متعدد الأسراب عبر MihwarRouter وSwarmOrchestrator مع توجيه حسب المجال لتسعة أسراب.
- code_evidence: NO EVIDENCE FOUND
- test_evidence: NO TEST FOUND
- runtime_evidence: NOT VERIFIED
- actual_status: MISSING
- gap_description: لا يوجد تنفيذ باسم MihwarRouter أو SwarmOrchestrator أو عدّاد 9 swarms داخل هذا المستودع.

## PAT-007 — RAPTOR Sovereign Gateway — centralized LLM gateway, sovereign-first priority, permanent provider blocking
- claim_summary: بوابة LLM مركزية بأولوية سيادية أولاً مع حجب دائم لمزوّدين محددين.
- code_evidence: src/services/unifiedAgentAdapter.ts:911-911
- test_evidence: NO TEST FOUND
- runtime_evidence: NOT VERIFIED
- actual_status: WEAK
- gap_description: يوجد ذكر RAPTOR كنص إرشادي فقط، دون تنفيذ gateway مركزي مثبت أو آلية provider blocking دائمة.

## PAT-008 — Falak Synthetic Testing — 7 synthetic agents, 140 questions, per-sector benchmark
- claim_summary: إطار اختبار تركيبي بسبعة وكلاء و140 سؤالًا مع معيار أداء لكل قطاع.
- code_evidence: NO EVIDENCE FOUND
- test_evidence: NO TEST FOUND
- runtime_evidence: NOT VERIFIED
- actual_status: MISSING
- gap_description: لا يوجد إطار Falak أو أرقام 7/140 أو بنية benchmark قطاعية مثبتة بالكود.

## PAT-009 — SARAB Security Doctrine — 10 shadow monitors, Board Gatekeeper 3-of-3, auto-quarantine
- claim_summary: عقيدة أمنية تشمل 10 مراقبين ظل وبوابة مجلس 3/3 مع عزل تلقائي.
- code_evidence: NO EVIDENCE FOUND
- test_evidence: NO TEST FOUND
- runtime_evidence: NOT VERIFIED
- actual_status: MISSING
- gap_description: لا يوجد تنفيذ لعناصر 10 monitors أو 3-of-3 gatekeeper أو auto-quarantine.

## PAT-010 — Arabic Semantic Similarity — bge-m3 embeddings, contextual thresholds (NUMERICAL 0.97, REGULATORY 0.88, PROCEDURAL 0.82, GENERAL 0.85), Jaccard fallback
- claim_summary: قياس تشابه دلالي عربي باستخدام bge-m3 وحدود قرار سياقية مع fallback عبر Jaccard.
- code_evidence: .agents/ingest_test.py:60-61
- test_evidence: NO TEST FOUND
- runtime_evidence: NOT VERIFIED
- actual_status: WEAK
- gap_description: يوجد استخدام bge-m3 للإدخال/التضمين فقط، دون محرك similarity بعتبات NUMERICAL/REGULATORY/PROCEDURAL/GENERAL أو Jaccard fallback.

## PAT-013 — Legislative Adaptation — Gazette monitor, content hashing, impact analyzer, human review for HIGH
- claim_summary: تكيّف تشريعي يراقب الجريدة الرسمية ويحلل الأثر ويُلزم مراجعة بشرية للحالات عالية الخطورة.
- code_evidence: NO EVIDENCE FOUND
- test_evidence: NO TEST FOUND
- runtime_evidence: NOT VERIFIED
- actual_status: MISSING
- gap_description: لا يوجد Gazette monitor أو impact analyzer أو مسار human review for HIGH مثبت بالكود.

## PAT-014 — Auditable Reasoning Chain — ReasoningChainBuilder middleware, DecisionCertificate with SHA-256 of full chain
- claim_summary: سلسلة استدلال قابلة للتدقيق عبر middleware مخصص وشهادة قرار تتضمن SHA-256 لسلسلة كاملة.
- code_evidence: .agents/validators/qala_audit_sink.py:3-5,107-109,197-209
- test_evidence: tests/test_qala_audit_sink.py:47-64 + passing
- runtime_evidence: NOT VERIFIED
- actual_status: WEAK
- gap_description: الموجود hash-chained audit sink، لكن لا يوجد ReasoningChainBuilder ولا DecisionCertificate يحمل hash لسلسلة reasoning كاملة.

## PAT-018 — Cross-Sector Conflict Detection — 5 regulators, constraint parser, conflict types (DIRECT_CONTRADICTION/PARAMETER_MISMATCH/AMBIGUOUS_OVERLAP), context-dependent priority
- claim_summary: كشف تعارضات بين قطاعات تنظيمية متعددة عبر parser للقيود وأنواع تعارض محددة وأولوية حسب السياق.
- code_evidence: NO EVIDENCE FOUND
- test_evidence: NO TEST FOUND
- runtime_evidence: NOT VERIFIED
- actual_status: MISSING
- gap_description: OUT OF SCOPE: in LexPrim/Qarar conflict-detector packages حسب التوثيق، وليس في swarms الحالي.

## Summary
- STRONG: 0
- MEDIUM: 1
- WEAK: 5
- MISSING: 7
- OUT_OF_SCOPE: 2

## Critical Gaps
- PAT-001: لا يوجد TruthGate/LLM Bridge مثبت؛ الدليل يقتصر على AuditTrail.
- PAT-002: لا يوجد تنفيذ BFT بخمسة وكلاء أو 3-of-5 أو multiplicative confidence.
- PAT-003: غياب DATA_CLASSIFICATION و selectProviderByClassification() و permanently-blocked providers.
- PAT-004: غياب ML cascade المطلوب (CodeBERT/ModernBERT/BERT-small) وغياب SLA <200ms وWARNING verdict.
- PAT-005: OUT OF SCOPE: in LexPrim/Qarar monorepo؛ لا دليل داخل swarms.
- PAT-006: لا يوجد MihwarRouter/SwarmOrchestrator أو 9 swarms.
- PAT-007: RAPTOR مذكور نصيًا فقط دون تنفيذ gateway مثبت.
- PAT-008: لا يوجد Falak synthetic suite (7 agents/140 questions).
- PAT-009: لا يوجد SARAB doctrine (10 monitors + 3-of-3 + auto-quarantine).
- PAT-010: bge-m3 موجود للـ embeddings فقط دون thresholds/Jaccard engine.
- PAT-013: لا يوجد Gazette monitor/impact analyzer/human-review-for-HIGH.
- PAT-014: لا يوجد ReasoningChainBuilder/DecisionCertificate كما في المطالبة.
- PAT-018: OUT OF SCOPE: in LexPrim/Qarar conflict-detector packages.
