# نظرة عامة على برنامج CurLexAI / swarms

> **الغرض:** تقرير مرجعي يلخّص هوية البرنامج، آلية العمل، السياسة الإدارية، طبقات الواجهة الأمامية والخلفية، أسماء الوكلاء والنماذج التي يعملون عليها، وحالة براءات الاختراع — مع التزام دقيق بمصفوفة الأدلة (`VERIFIED` / `INFERRED` / `UNVERIFIED`).
>
> **متى يُحمَّل:** عند الحاجة إلى نظرة شاملة دون قراءة كل ملفات الحوكمة بشكل منفصل. لا يُستخدم بديلاً عن `ADR-0001-swarms-boundary.md` ولا عن `AGENTS.md`.

---

## 1) هوية المستودع وحدوده

- `CurLexAI/swarms` هو **طبقة تشغيل الوكلاء والتحقق والـ sovereign data pipelines**، وليس monorepo لتطبيق LexPrim / Qarar.
- يعمل تحت مؤسسة **LexPrime** على GitHub Enterprise: `https://github.com/enterprises/lexprime`. ضوابط SSO، IP allowlists، secret scanning، Advanced Security مُدارة على مستوى المؤسسة وتُورَّث هنا.
- المرجع الرسمي للحدود: `docs/decisions/ADR-0001-swarms-boundary.md`.

**المحتوى المسموح به (خمس فئات فقط):**
1. تشغيل الوكلاء (`.agents/`): catalog، config، providers، router، validators.
2. غراء وقت تشغيل Modal: `.agents/modal_app.py` ومحوّلات `src/services/`.
3. بوابات التحقق: `tests/`، `scripts/commander/`، `.agents/validators/`.
4. المهارات والسياسات ووثائق العمليات.
5. خطوط الـ Sovereign Data Pipelines الخاصة (Modal/Qdrant).

**ممنوع منعاً قاطعاً:** `backend_fastapi/`، `src/routes/`، `src/api/`، صفحات تسويقية في `public/`، أي pipeline RAG عام، واجهات REST/GraphQL عمومية، أو علم `autoStart` على أي وكيل.

---

## 2) كيف تم إنشاء البرنامج وكيف يعمل

### الطوبولوجيا الرسمية (Canonical Topology)

```text
User / iPhone / GitHub / Copilot
  -> Codex Commander
  -> Repository worktree
  -> Render origin
  -> Cloudflare edge
  -> Modal sovereign model runtime (Bayyinah / Mihwar via vLLM)
  -> Bayyinah validation gate
```

### تدفق العمل الافتراضي (Collaboration Protocol)

1. **Mihwar** يستلم المهمة → يبني الخطة + التنفيذ.
2. **Bayyinah** تستلم مخرجات Mihwar للمراجعة الأمنية والمنطقية.
3. عند `REQUEST_CHANGES` → يعدّل Mihwar (حد أقصى **3 دورات**).
4. تصعيد للبشر عند تجاوز الحد أو وجود نتيجة `CRITICAL` / `HIGH` غير محلولة.
5. **اعتماد بشري إلزامي** لأي:
   - تعديل في `.github/workflows/`
   - تعديل CODEOWNERS
   - إضافة/إزالة dependency
   - تغيير schema قاعدة بيانات
   - تغيير API contract عام
   - أي finding بمستوى CRITICAL بقي بعد ثلاث دورات

### نمط التشغيل (Operating Model)

- **Codex Commander**: قائد التنفيذ — يحدّد النطاق، يخطّط PRs صغيرة، يشغّل البوابات، يصدر تقرير `COMMANDER REPORT`.
- **Bayyinah**: بوابة التحقق والمراجعة — تفعيلها التشغيلي يبقى `UNVERIFIED` حتى تنجح smoke tests على الـ endpoint.
- **Mihwar**: وكيل التنفيذ واقتراح الإصلاحات — لا يُعتبر حياً قبل ضبط `MIHWAR_ENDPOINT` و `AGENT_API_TOKEN` وإثبات اختبار حي.
- **Render**: مصدر التطبيق (origin).
- **Cloudflare**: طبقة الـ edge (DNS/TLS/WAF).
- **Modal**: وقت تشغيل النماذج فقط — **backend-only** — يُحظر استدعاء `*.modal.run` من المتصفح أو iPhone أو أي سطح عام.

---

## 3) السياسة العامة الإدارية

### مصفوفة الحالة الإلزامية (Status Labels)

`VERIFIED` | `INFERRED` | `UNVERIFIED` | `SKIPPED_UNVERIFIED` | `NOT_APPLICABLE`

وعلى مستوى تنفيذ Claude:
`VERIFIED_FIXED` | `PARTIALLY_APPLIED` | `CHANGED_BUT_NOT_VERIFIED` | `BLOCKED` | `UNVERIFIED` | `NOT_STARTED` | `SUPERSEDED` | `CONFLICTED`.

### السياسات الإلزامية (mandatory boundaries)

| السياسة | الملف |
|---|---|
| Secrets Boundary | `.agents/policies/secrets-boundary.md` |
| Network Boundary | `.agents/policies/network-boundary.md` |
| Dependency Build Safety | `.agents/policies/dependency-build-safety.md` |
| Execution Discipline Maximum | `.agents/policies/execution-discipline-maximum.md` |
| Qala Egress Residency | `.agents/policies/qala-egress-residency.md` |

### المحظورات المطلقة (Absolute Prohibitions)

1. لا التزام بملفات `.env` ولا اعتماد حقيقي ولا توكنات ولا مفاتيح SSH ولا توكنات GitHub.
2. لا كشف لنقاط Modal على أي سطح عام (متصفح/iPhone/frontend).
3. لا ادعاء امتثال SAMA / PDPL / NCA دون دليل مُستشهد به.
4. لا استدعاء APIs خارجية للذكاء الاصطناعي أثناء عمل المستودع إلا بإذن صريح.
5. لا تشغيل scripts للتثبيت أو lifecycle dependencies بدون مراجعة سلامة dependency.
6. لا الالتزام بـ `node_modules` أو build outputs أو caches.
7. لا دمج PR فيه `CRITICAL` أو `HIGH` غير محلول.
8. لا merge / force-push / production deploy / rotate secrets / تعديل فوترة بدون موافقة المستخدم الصريحة.
9. أوامر عريضة مثل "نفّذ كل شيء" **لا** تعطي صلاحية لحذف ملفات الحوكمة أو تجاوز السياسات.

### بوابات الـ Commander (يجب أن تمر قبل الإعلان عن الجاهزية)

```bash
bash scripts/commander/p0-security-test-gate.sh .
bash scripts/commander/modal-boundary-gate.sh .
bash scripts/commander/adr-0001-boundary-gate.sh .
bash scripts/commander/agent-presence-gate.sh .
bash .agents/skills/codex-commander/scripts/codex_commander_gate.sh .
```

بوابات إضافية على الـ surface العام والـ egress: `public-surface-boundary-gate.sh`، `qala-egress-residency-gate.sh`، `repo-rename-gate.sh`.

---

## 4) واجهات الـ Website

> هذا المستودع **ليس** الموقع العام للمنتج. لذلك لا يوجد فيه صفحات تسويق / dashboards / واجهات مستخدم نهائية. السطح الوحيد العام المسموح به محصور في صفحة الثقة (Trust Center).

| المسار | الوصف |
|---|---|
| `public/trust/index.html` | **Trust Center** — صفحة HTML واحدة بالعربية RTL تعرض ضوابط الثقة بـ `VERIFIED` / `UNVERIFIED`: Data Residency، Encryption، Access Control، Model Governance، Audit Logging، Incident Response، ومواءمة PDPL / SAMA CSF / NCA ECC (كل ذلك بنطاق مُقيَّد ودون ادعاء امتثال نهائي). |
| `public/trust/vendor/` | أصول الـ frontend الموقّعة عبر SRI. |
| `public/trust/cdn-integrity.json` | مرجع تكامل SRI لأصول الـ CDN. |

التحقق من سلامة الـ CDN عبر:
```bash
npm run integrity:frontend
npm run check:cdn-sri
npm run test:cdn-sri
```

أي صفحة عامة أخرى (`/about`، `/contact`، `/privacy`، `/terms`، `/`) **ممنوعة** بحسب ADR-0001.

---

## 5) الـ Backend

`src/backend/` و `src/services/` ليسوا تطبيقاً عاماً — هم **محوّلات تشغيل للوكلاء**:

| المكوّن | الوظيفة |
|---|---|
| `src/backend/chatApi.ts` / `.js` | غلاف Chat API يستخدمه المحوّل الموحّد. |
| `src/services/unifiedAgentAdapter.ts` / `.js` | المحوّل الموحّد — يقرأ `agents/registry.yaml`، يتحقق من الـ payload، يفوّض الصلاحية عبر `PolicyService`، ثم يوزّع على runtime بايثوني أو Node. |
| `src/services/AuditService.ts` / `.js` | خدمة التدقيق — أحداث، تتبّع، تحديث حالة المهام. |
| `src/services/ControlPlaneSecurityService.ts` | خدمة أمن طبقة التحكم (ملف `.js` المتولّد من tsc مُستثنى من Git). |
| `src/services/agentRelayService.ts` | ترحيل استدعاءات الوكيل عبر runtime آمن. |
| `src/runners/clientAgentRelay.ts` | جسر طرف العميل لـ relays الوكيل. |
| `src/security/sovereignCyberRadar.ts` / `.js` | ماسح أمني CLI (`npm run security:radar:*`). |
| `src/security/qalaAuditSink` / `qalaKsaPii` / `qalaTrace` | سلاسل تدقيق Qala، PII، Trace. |
| `src/security/bayyinahRedactor.ts` | حاجب Bayyinah للبيانات الحساسة قبل الإرسال. |
| `src/security/contentSecurityPolicy.ts` | تكوين CSP للأسطح المسموح بها. |
| `src/models/modelRegistry.ts` | قارئ JSON لـ `config/models.registry.json` (Ollama / Modal / openai-compatible / local-file). |
| `src/utils/auditLogger`, `src/utils/logger` | مرافق التسجيل والتدقيق. |

### Modal Runtime (`.agents/modal_app.py`)

- يعرّف Modal App اسمها `curlexai-agents`.
- يحوي endpoint `MihwarAgent` (2× A100-80GB، vLLM، tensor parallel 2).
- يحوي endpoint `BayyinahAgent` (1× A100-80GB، vLLM).
- نقاط النهاية محميّة بـ HMAC bearer token (`AGENT_API_TOKEN`).
- الأسرار من Modal: `huggingface-secret`، `agent-api-secret`.

### مصدر النشر

`render.yaml` لمصدر Render، Cloudflare على الـ edge، وأذونات سرية تُضبط فقط في GitHub Actions / Render / Modal Dashboard (راجع `docs/secrets-policy.md`).

---

## 6) أقسام الـ Frontend (وغير المتصفّحية)

| القسم | اللغة/المنصة | الموقع |
|---|---|---|
| **Trust Center الوحيد على الـ Web** | HTML/CSS/JS بسيط، RTL عربي | `public/trust/` |
| **iOS Companion (Mihwar)** | Swift / SwiftUI + WireGuard | `ios-companion/MihwarCompanion/` — ملفات: `MihwarCompanionApp.swift`، `ContentView.swift`، `PolicyService.swift`، `PostureCollector.swift`، `WireGuardService.swift` |
| **Windows Agent** | C# (.NET) | `windows-agent/` — `AgentWorker.cs`، `CellularAdapter.cs`، `NetworkEnforcer.cs`، `PolicyEngineClient.cs`، `QuicTransport.cs`، `TelemetryCollector.cs` |
| **Mihwar Core** | Go | `mihwar-core/` — `cmd/`، `internal/`، Dockerfile |
| **Dev Factory** | Node | `dev-factory/` — config/scripts/src |
| **Sovereign Connectivity POC** | متعدد | `sovereign-connectivity-poc/`، `sovereign_network_agent_systemd_v1/` |
| **Qarar Integration Overlay** | Bash + Markdown | `qarar-swarms-sovereign-integration/` |
| **Plugins** | Node | `plugins/unified-agent-adapter/` |
| **MCP Server** | YAML/Python | `.agents/mcp/` لتكامل GitHub Copilot |

---

## 7) النماذج التي يعمل عليها الوكلاء

### النماذج المُعلَنة في `.agents/config/agents.yaml` (مصدر الحقيقة)

| الوكيل | النموذج | الحجم | License | Context | HumanEval |
|---|---|---|---|---|---|
| **Mihwar** (المحور) | `deepseek-ai/DeepSeek-Coder-V2-Instruct` | 236B MoE (21B active) | DeepSeek Model License | 128K | 90.2 |
| **Bayyinah** (البيّنة) | `Qwen/Qwen2.5-Coder-32B-Instruct` | 32B | Apache 2.0 | 131K | 92.7 |

### Inference Engine

كلاهما يعمل على **vLLM** فوق Modal A100-80GB:
- Mihwar: `temperature=0.1`، `top_p=0.95`، `max_tokens=8192`، `tensor_parallel_size=2`، `keep_warm=1`، `gpu_count=2`.
- Bayyinah: `temperature=0.0`، `top_p=1.0`، `max_tokens=4096`، `tensor_parallel_size=1`، `concurrency_limit=4`، `gpu_count=1`.

### سجل النماذج الإضافي `config/models.registry.json`

| id | provider | model | profile |
|---|---|---|---|
| `qwen-coder-local` | Ollama | `qwen2.5-coder:32b` | code_local |
| `bayyinah-legal-local` | Ollama | `qwen2.5:14b-instruct` | local_only |
| `mihwar-legal-modal` | Modal | `qwen-legal-finetune` | sanitized_cloud |
| `gpt-review-gateway` | OpenAI-compat | `gpt-4.1` | sanitized_cloud |

### مزوّدو النماذج المعرّفون في `.agents/providers/`

- `modal_provider.py` (السيادي — أساس Bayyinah/Mihwar)
- `openai_provider.py` (مغلق خلف `ALLOW_EXTERNAL_AI=true`)
- `anthropic_provider.py` (مغلق خلف نفس البوابة)
- `types.py` (أنواع موحّدة)

---

## 8) عدد الوكلاء وأسماؤهم وأقسامهم

### الوكيلان الأساسيان في `.agents/config/agents.yaml`

| # | المعرّف | الاسم العربي | الدور | Tier |
|---|---|---|---|---|
| 1 | `mihwar` | المحور | Senior Architect / Code Generator | 1 |
| 2 | `bayyinah` | البيّنة | Code Reviewer / Validator | 2 |

> **ملاحظة:** `copilot_swe` و `.github/agents/*.agent.md` (وكلاء GitHub Copilot Custom) أُزيلوا. الاستدعاء يتم الآن عبر CLI / MCP / Sovereign Gateway فقط.

### سجل الوكلاء الموسّع في `agents/registry.yaml` (legacy fallback — 7 وكلاء + 1)

1. `mihwar` — Modal vLLM، DeepSeek-Coder-V2-Instruct
2. `bayyinah` — Modal vLLM، Qwen2.5-Coder-32B-Instruct
3. `qarar-router` — موجّه نماذج محلي يعتمد السياسات
4. `deepseek-coder` — alias مباشر للنموذج الأساس
5. `qwen-coder` — alias مباشر للنموذج الأساس
6. `azure-gpt` — Azure OpenAI (UNVERIFIED حتى ضبط الـ env)
7. `gpt-o1` — OpenAI o1 (UNVERIFIED حتى ضبط الـ env)
8. `pr-fix-conflict` — حل تعارضات الـ PRs (Qwen2.5-Coder via Bayyinah endpoint)

### الأسراب (Swarms) المعرّفة

| الـ Swarm | الأعضاء | الـ Pipeline |
|---|---|---|
| `coding-swarm` (سرب البرمجة) | mihwar → bayyinah | `mihwar.review_and_generate` → `bayyinah.review` |
| `routing-swarm` (سرب التوجيه) | qarar-router → bayyinah | `classify` → `choose_route` → `bayyinah.review` |

### الأقسام الوظيفية داخل `.agents/`

| القسم | الموقع | الوصف |
|---|---|---|
| Catalog | `.agents/catalog/agents.yaml` | كتالوج عرض |
| Config | `.agents/config/agents.yaml` | **المصدر الرسمي للحقيقة** |
| Gateway | `.agents/gateway/` | بوابة استدعاء الوكلاء |
| MCP | `.agents/mcp/` | تكوين خادم MCP لـ Copilot |
| Plugins | `.agents/plugins/` | إضافات الوكلاء |
| Providers | `.agents/providers/` | محوّلات Modal/OpenAI/Anthropic |
| Registries | `.agents/registries/` | سجلات Skills الذكية |
| Router | `.agents/router/` | مصنّف المهام + محرّك السياسة + الموجّه |
| Validators | `.agents/validators/` | بوابة Bayyinah البرمجية + Qala (Input / KSA-PII / Audit Sink / Trace) |
| Skills | `.agents/skills/` | playbooks: codex-commander، modal-runtime-operator، repo-production-auditor، ai-skill-bridge، agent-runtime-auditor، public-surface-auditor، hf-cli، iphone-command-center، ... |
| Policies | `.agents/policies/` | الحدود الإلزامية الخمس |
| Templates | `.agents/templates/` | قوالب التقارير |

---

## 9) خرائط التحقق والاختبار

| الفحص | الأمر |
|---|---|
| تجميع Python | `python3 -m py_compile .agents/*.py` |
| تحقق أصول الوكلاء | `python3 .agents/validate.py` |
| سرد الوكلاء | `python3 .agents/invoke.py info` |
| Pytest | `python3 -m pytest -q tests/` |
| اختبارات Node للمحوّل | `npm test` |
| اختبارات الوحدات فقط | `npm run test:unit` |
| اختبارات الأمان | `npm run test:security` |
| فحص TypeScript | `npx tsc --noEmit` (به blocker معروف يتم تتبّعه منفصلاً) |
| الفحص المجمَّع | `npm run check` |

> **آخر دليل launch evidence مُسجَّل:** عند الـ commit `57017b3a`، حالة الجاهزية المحلية `LOCAL_READY` — كل بوابات P0 والـ Python (171 اختبار) و Node (98 اختبار) تمر. التحقق من runtime مُعلَّق على إعداد الأسرار `BAYYINAH_ENDPOINT` / `MIHWAR_ENDPOINT` / `AGENT_API_TOKEN`.

---

## 10) براءات الاختراع — هل اكتملت؟

### الإجابة المختصرة

**لا.** بحسب التدقيق الرسمي الموثَّق في `docs/audits/full-audit-2026-04-19.md` (SECTION 2 — PATENT VERIFICATION) فإن **مسارات الإثبات** المعلَنة لكل براءات LexPrim / Qarar **مفقودة من هذا المستودع** لأنها تخص الـ monorepo المنتج (LexPrim / Qarar) لا طبقة `swarms` التشغيلية.

### تفصيل مصفوفة البراءات (حالة الكود — لا الحالة القانونية)

| ID | الاسم | المسار المتوقّع | الحالة |
|---|---|---|---|
| #1 | جدار الحماية MCP | `lexprim-core/patents/patent1_firewall/` | **MISSING** |
| #2 | سجل تنفيذ الوكلاء | `qarar/packages/bayyinah/src/audit/` | **MISSING** |
| #3 | رسم نسب المصادر القانونية | `backend_fastapi/tests/test_patent3_lineage.py` | **MISSING** |
| #4 | RAG ذاتي الإصلاح | `src/pipeline/qarar-rag-infra.py` | **MISSING** |
| #5 | الموجّه السيادي الديناميكي | `src/config/regulatory-intelligence-router.js` | **MISSING** |
| #6 | بوابة الجودة + circuit breaker | `src/` (بدون مسار مؤكَّد) | **UNVERIFIED** |
| #7 | اليقين BFT | `qarar/packages/bayyinah/src/yaqeen/` | **MISSING** |
| #8 | سراب phantom | `qarar/packages/bayyinah/src/sarab/agents/sarab-phantom.ts` | **MISSING** |
| #9 | واجهة الوكلاء القانونية | `qarar/packages/bayyinah/src/runner.ts` + `evidence.ts` + `authority.ts` | **MISSING** |
| #10 | SPIFFE zero trust | `qarar/packages/bayyinah/src/sarab/agents/sarab-arbiter.ts` | **MISSING** |
| #11 | الفريق الأحمر التشريعي | `qarar/packages/bayyinah/src/redteam/` | **MISSING** |
| #12 | محامي الشيطان | `qarar/packages/bayyinah/src/conflict/devil-advocate.ts` | **MISSING** |
| #13 | التوأم التنظيمي | `qarar/packages/bayyinah/src/conflict/regulatory-twin.ts` | **MISSING** |
| #14 | الذاكرة التنظيمية الجماعية | `qarar/packages/bayyinah/src/conflict/collective-regulatory-memory.ts` | **MISSING** |
| #15 | موجّه المحتوى التنظيمي | `src/config/regulatory-intelligence-router.js` | **MISSING** |
| #16 | محرك البيّنة QAR-PAT-001 | `src/bayyinah/truth-gate.js` + `bridge.ts` | **MISSING** |
| QAR-PAT-002 | BFT | `qarar/swarms/certainty/` + `src/bayyinah/bft-consensus.js` | **MISSING** |
| QAR-PAT-003 | Sovereign Routing | `sovereign_router.py` | **MISSING** |
| QAR-PAT-004 | Security Gate | `src/security/pre-execution-gate.js` | **MISSING** |
| QAR-PAT-005 | Sector Factory | `src/factory/sector-factory.js` | **MISSING** |
| QAR-PAT-008 | Legislative Watch | `qarar/packages/legislative-watch/src/` | **MISSING** |
| QAR-PAT-010 | Arabic Similarity | `qarar/packages/arabic-similarity/src/` | **MISSING** |
| QAR-PAT-013 | Legislative Watch | (تكرار 008) | **MISSING** |
| QAR-PAT-014 | Reasoning Chain | `qarar/packages/reasoning-chain/src/` | **MISSING** |
| QAR-PAT-018 | Conflict Detector | `qarar/packages/conflict-detector/src/` | **MISSING** |

### ما هو **موجود جزئياً** كدليل (Patent Evidence Matrix الفرعي)

من `sovereign_network_agent_systemd_v1/docs/audits/patent-evidence-matrix.md`:

- **Sovereign Network Guard** — تنفيذ محلي لحلقة `Sense → Analyze → Decide → Act` بحالة `PARTIAL_LOCAL_EVIDENCE`.
- **Audit Chains** — سجل JSONL append-only يولّده `network_health_guard.py`.

### الجانب القانوني/الإداري

- ملف `docs/ai-governance/instruction-architecture/03-domains/ip-and-patent-strategy.md` يوضّح أنه **سياسة تشغيلية فقط** ويُحيل أي ادعاء بملكية فكرية إلى:
  1. توثيق تاريخ الإنشاء عبر `git log`.
  2. تحديد ما هو مبتكر بالضبط.
  3. التمييز بين المفتوح المصدر والمملوك.
  4. **استشارة قانونية مختصة لتسجيل البراءات** — لا توجد شهادة تسجيل أو رقم تقديم رسمي في هذا المستودع.

### الخلاصة بشأن البراءات

| البُعد | الحالة |
|---|---|
| إثبات الكود لكل البراءات داخل `swarms` | **UNVERIFIED / MISSING** — لأنها تخص LexPrim / Qarar وليست هذه الطبقة. |
| إثبات قانوني (رقم تقديم، شهادة تسجيل، براءة ممنوحة) | **UNVERIFIED** — غير موجود في المستودع، ويستوجب التحقق من جهة قانونية مختصة. |
| اكتمال البراءات | **لا — لم تكتمل تقنياً ولم يُوثَّق اكتمالها قانونياً داخل هذا المستودع.** |

التوصية: **عدم الادعاء بـ "براءات مكتملة" في أي وثيقة عامة أو صفحة Trust** حتى يتم:
- تجميع أدلة كود البراءات في الـ monorepo الصحيح (LexPrim / Qarar).
- استكمال إجراءات التقديم القانوني (مكتب براءات معتمد) والحصول على أرقام تقديم رسمية.
- ربط كل براءة بـ `evidence_path` حقيقي في الشجرة الإنتاجية وتوثيق ذلك في `docs/audits/`.

---

## 11) مراجع أساسية يجب قراءتها قبل أي تغيير

1. `AGENTS.md` — دليل الوكلاء (يُقرأ أولاً).
2. `CLAUDE.md` — تعليمات Claude داخل المستودع.
3. `README.md` — قائمة أوامر التحقق التشغيلية.
4. `INSTRUCTION_LOADING_ORDER.md` — ترتيب تحميل التعليمات.
5. `docs/decisions/ADR-0001-swarms-boundary.md` — الحدود الرسمية.
6. `docs/decisions/ADR-0003-qala-security-architecture.md` — هندسة أمن Qala.
7. `docs/decisions/ADR-0004-qala-modal-edge-hmac-auth.md` — مصادقة الـ Modal HMAC.
8. `docs/secrets-policy.md` — سياسة الأسرار.
9. `docs/launch-evidence/agent-launch.md` — قالب أدلة الإطلاق.
10. `.agents/skills/codex-commander/SKILL.md` — عقيدة Codex Commander التشغيلية.

---

## 12) ختام (Verdict)

- **هوية البرنامج:** طبقة تشغيل ووكلاء وتحقق للبرنامج الأم CurLexAI.
- **النموذج التشغيلي:** ثلاثي الوكلاء الأساسي (Mihwar / Bayyinah / Copilot SWE) مع سجل موسَّع لسبعة وكلاء ومزوّدَين خارجيين معطّلَين افتراضياً.
- **الواجهات العامة:** Trust Center فقط (`public/trust/`).
- **الخلفية:** Modal سيادي backend-only، Render origin، Cloudflare edge، اعتمادات في Secret Managers لا في الـ repo.
- **براءات الاختراع:** **لم تكتمل** — لا تقنياً (أدلة الكود مفقودة من هذا المستودع لأنها تخص الـ monorepo الإنتاجي) ولا قانونياً (لا أرقام تقديم/شهادات تسجيل موثَّقة هنا).
- **الجاهزية الحالية:** `LOCAL_READY` — كل بوابات P0 والاختبارات تمر، runtime activation معلَّق على ضبط `BAYYINAH_ENDPOINT` و `MIHWAR_ENDPOINT` و `AGENT_API_TOKEN` ثم تشغيل smoke tests فعلية ضد Modal.
