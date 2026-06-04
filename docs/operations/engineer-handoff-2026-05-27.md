# Engineer Handoff Report — 2026-05-27

> وثيقة تسليم شاملة لمهندس مكمِّل. يلخص هذا التقرير ما تم تنفيذه فعلياً، وما لم يكتمل، والمخاطر الحدودية المعلّقة، والإجراءات التالية الموصى بها. مبني على فحص مستودع `CurLexAI/swarms` على فرع `claude/repository-code-review-fMaxs` بتاريخ 2026-05-27.

---

## 1. ملخص الحالة (Executive Summary)

- **الكود الأساسي**: مكتمل من حيث البنية (وكلاء، موجِّه، مدققون، مهايئ Node، MCP). الوظيفة عبر التشغيل غير المُتحقَّق منه.
- **التحقق المحلي**: 12 بوابة/مجموعة اختبار تمر، **5 تفشل**، منها 2 بسبب أخطاء سكربتات (وليست منطق إنتاج)، 1 جوهرية (`npm test` — 8 إخفاقات في `unifiedAgentAdapter`).
- **التحقق التشغيلي (Runtime)**: لم يُكمَل. أسرار Modal/Render/Cloudflare غير مضبوطة، ولا يوجد دليل اختبار دخان ناجح موقَّع.
- **التسليم البشري**: قسم Sign-off في `docs/launch-evidence/agent-launch.md` لا يزال `PENDING` — لم يُسجَّل أي اعتماد مشغّل.
- **انحراف الحدود (Boundary Drift)**: 7 مجلدات على مستوى الجذر تشبه شيفرة منتج (`mihwar-core/`, `ios-companion/`, `windows-agent/`, إلخ) خارج النطاق المسموح به في ADR-0001 لكنها غير محظورة صراحةً في السكربت الحالي — يجب الحسم.

---

## 2. ما تم تنفيذه (Implemented — VERIFIED)

### 2.1 طبقة وقت تشغيل الوكلاء `.agents/`

| الملف | الحالة | الوظيفة |
|---|---|---|
| `modal_app.py` | VERIFIED — تجميع نظيف | فئتا `MihwarAgent` (سطر 81) و`BayyinahAgent` (175) + ثلاث نقاط ويب: `bayyinah_review_web`، `mihwar_generate_web`، نقاط اختبار محلية. |
| `invoke.py` | VERIFIED — `info` يعمل | CLI: `mihwar`, `bayyinah --file/--diff/--code`, `pipeline`, `info`. يتضمن محلل YAML احتياطي. |
| `pr_review.py` | VERIFIED — يُجمَّع | يستدعى من `.github/workflows/agent-review.yml`؛ يقرأ diff، يستدعي Modal، يُعلِّق على PR. |
| `validate.py` | VERIFIED — يمر | يتأكد من وجود 7 ملفات أصول مطلوبة. |
| `router/` | VERIFIED — اختبارات تمر | `task_classifier → model_policy_engine → model_router` ينتج `ExecutionPlan`. |
| `validators/bayyinah_validation_gate.py` | VERIFIED | بوابة تحقق برمجية + اختبارات P0. |
| `validators/qala_*.py` | VERIFIED — اختبارات تمر | `qala_audit_sink` (سجل مُسلسَل بالتجزئة)، `qala_input_gate`، `qala_ksa_pii`، `qala_trace`. |
| `providers/{modal,openai,anthropic}_provider.py` | INFERRED — هياكل وظيفية | تجريدات مزوّدين. |
| `config/agents.yaml` | VERIFIED | Mihwar = `deepseek-ai/DeepSeek-Coder-V2-Instruct` (2×A100-80GB)؛ Bayyinah = `Qwen/Qwen2.5-Coder-32B-Instruct` (1×A100-80GB). |
| `mcp/server.py` | VERIFIED — يُجمَّع | خادم MCP عبر stdio يكشف: `mihwar_generate`, `bayyinah_review`, `free_birds_review`, `free_birds_design`. |
| `mcp/cloudflare-mcp/` | INFERRED — يحتاج deploy لتأكيد | Workers MCP مع OAuth، 7 ملفات TS، `wrangler.jsonc`. |

### 2.2 طبقة Node/TS `src/`

| الملف | الحالة | ملاحظات |
|---|---|---|
| `services/unifiedAgentAdapter.ts/.js` | PARTIALLY_APPLIED | جوهر المهايئ موجود، لكن `npm test` يُظهر 8 إخفاقات (انظر §3.1) و`check:service-divergence` يفشل (انظر §3.2). |
| `services/AuditService.{ts,js}` | VERIFIED | كاتب سجل مدقق مُهيكل. |
| `services/ControlPlaneSecurityService.ts` | VERIFIED — اختبار يمر | الـ `.js` مُولَّد ومُستثنى من Git. |
| `services/agentRelayService.ts` + `runners/clientAgentRelay.ts` | INFERRED | غراء وقت تشغيل لإعادة توجيه الوكيل. |
| `security/sovereignCyberRadar.ts` | VERIFIED — 8/8 اختبارات أمنية تمر | CLI: `scan-url`, `scan-text`, `scan-command`, `simulate`. |
| `security/bayyinahRedactor.ts` | VERIFIED — اختبار يمر | حاجب PII. |
| `security/contentSecurityPolicy.ts` | VERIFIED — اختبار يمر | |
| `models/modelRegistry.ts` | VERIFIED | فهرس النماذج. |
| `backend/chatApi.{ts,js}` | VERIFIED — اختبار يمر | واجهة محادثة. |

### 2.3 سير العمل والاختبارات

- **GitHub Actions** (11 سير): `agent-review`, `bayyinah-swe`, `mihwar-swe`, `free-birds-swe`, `constitutional-compliance`, `frontend-sri`, `modal-runtime-activation`, `smoke-modal`, `opencode`, `pdpl-article22-ingestion`, `qarar-fastconnect-deploy`.
- **اختبارات Python**: 173 اختبار يمر، 2 تخطّى. تغطي router، Bayyinah gate، PR review، مجموعة Qala، بوابات الحدود.
- **اختبارات Node**: 21 يمر + 8 يفشل + 1 يتخطى من 30 اختبار `unifiedAgentAdapter`. مجموعات `chatApi`/`agentRelay`/`controlPlaneSecurity`/`cdn-sri`/`csp`/`sovereignCyberRadar`/`bayyinahRedactor`/`modelRegistry`/`qala*` تمر.

### 2.4 المهارات والسياسات

- 7 مهارات بمجلدات كاملة (`codex-commander`، `agent-runtime-auditor`، `ai-skill-bridge`، `hf-cli`، `modal-runtime-operator`، `public-surface-auditor`، `repo-production-auditor`) + 10 ملفات مهارات مسطحة.
- 5 سياسات: `dependency-build-safety`، `execution-discipline-maximum`، `network-boundary`، `qala-egress-residency`، `secrets-boundary`.
- ADRs 0001–0006 موجودة (لكن انظر §4.3).

---

## 3. ما لم يُنفَّذ / لم يُتحقَّق منه (Open Items)

### 3.1 ❌ إخفاقات `npm test` — 8 اختبارات (P0)

كلها في `tests/unifiedAgentAdapter*` (اختبارات 3, 12, 13, 15, 19, 20, 21, 22). تغطي:
- إعادة المحاولة (retries)
- توجيه وقت تشغيل Node
- التحقق من حمولة المرحلة التالية
- `CONFIG_NOT_FOUND`
- `ERR_MODULE_NOT_FOUND`

**التشخيص المرجح**: مرتبط بـ §3.2 — انحراف TS↔JS في `unifiedAgentAdapter`. الإصلاح: مزامنة `.js` مع `.ts` (أو العكس) وإعادة تشغيل المجموعة.

### 3.2 ❌ `check:service-divergence` يفشل

`src/services/unifiedAgentAdapter.ts` و`.js` لم يعودا متطابقَين. القاعدة في `CLAUDE.md`: الـ `.js` يدويّ-الصيانة ومُتعقَّب. يجب أن يقرر المهندس المكمِّل أيّ الملفين هو المرجع ويزامن الآخر.

### 3.3 ❌ بوابة الجاهزية للإطلاق `release-readiness-gate.sh`

تفشل بسبب تتالي إخفاقات `npm test` + أسرار وقت التشغيل غير مضبوطة. ستمر بعد إصلاح §3.1 وحقن الأسرار.

### 3.4 ⚠️ أخطاء سكربتات بوابة (ليست منطق إنتاج)

| السكربت | الخطأ |
|---|---|
| `scripts/commander/p0-security-test-gate.sh` | `ModuleNotFoundError: No module named 'PYTHON_BIN='` — مسند البيئة `PYTHON_BIN=...` يُمرَّر كاسم وحدة Python بدلاً من تعيين بيئة. |
| `scripts/commander/agent-presence-gate.sh` | يمرر صياغة `bash` (`[[ -z "$PYTHON_BIN" ]]`) إلى مفسر Python — `SyntaxError`. |

**الإصلاح المقترح**: مراجعة كيفية استدعاء `python3` في كلا السكربتَين (يبدو أنهما يَفترضان `env PYTHON_BIN=python3 python -c …` لكن الصياغة الفعلية مكسورة).

### 3.5 ❌ تنشيط وقت التشغيل (Runtime Activation)

من `docs/launch-evidence/agent-launch.md`:

| البند | الحالة |
|---|---|
| `BAYYINAH_ENDPOINT` | UNVERIFIED |
| `MIHWAR_ENDPOINT` | UNVERIFIED |
| Endpoint-specific API tokens | UNVERIFIED |
| اختبار دخان Bayyinah | SKIPPED_UNVERIFIED |
| اختبار دخان Mihwar | SKIPPED_UNVERIFIED |
| Render API | SKIPPED_UNVERIFIED |
| Cloudflare | SKIPPED_UNVERIFIED |
| تشغيل سير العمل | SKIPPED_UNVERIFIED |
| Sign-off المشغّل | PENDING |

**الإجراء**: حقن الأسرار في GitHub Actions/Modal، تشغيل `bash scripts/commander/modal-runtime-smoke.sh`، توقيع `agent-launch.md`.

### 3.6 ❌ `npx tsc --noEmit` — حاسم معروف (Known Blocker)

`CLAUDE.md` يذكر إخفاق `TS2307: Cannot find module '../runners/agentRunner.js'` في `unifiedAgentAdapter.ts`. **ملاحظة**: التشغيل الحالي أعاد `PASS` — قد يكون الخطأ مُحلّاً، أو متغيرات تخزين tsc مؤقتة. يجب التحقق صراحةً قبل اعتباره مُغلَقاً.

### 3.7 ⚠️ ADRs غير مكتملة

| ADR | الحالة | الإجراء |
|---|---|---|
| ADR-0001 | Accepted | ✓ |
| ADR-0002 | **مكرر — ملفان بنفس الرقم** | `ADR-0002-operator-static-artifacts-boundary.md` و`ADR-0002-repo-identity.md` — يجب إعادة ترقيم أحدهما إلى 0007. |
| ADR-0003 | Accepted (architecture only) | ✓ |
| ADR-0004 | **Proposed** | تصميم HMAC غير مُنفَّذ. قرار: نُنفِّذ أم نُحوِّل إلى Superseded. |
| ADR-0005 | Decided — Option A | ✓ |
| ADR-0006 | Decided — Secondary-only | الحالة `CHANGED_BUT_NOT_VERIFIED` (سطر 336) — يحتاج تحقق. |

### 3.8 ⚠️ ادعاءات براءات الاختراع غير مُتحقَّقة

من `docs/audits/patent-verification-audit-v2.md`:
- **PAT-001** MEDIUM — وقت التشغيل غير مُتحقَّق.
- **PAT-002** MISSING — لا يوجد تنفيذ BFT.
- **PAT-003** WEAK — لا يوجد تعداد `DATA_CLASSIFICATION`.

إذا كانت محفظة براءات الاختراع تعتمد على هذا المستودع، فهذه فجوة جوهرية.

### 3.9 ⚠️ انحراف حدود PR #176

`docs/audits/pr-176-sovereign-connectivity-poc-boundary-audit-2026-05-19.md` يُعلِّم انحراف Fastify من PR #176 (commit `a791273`). التدقيق **تقرير-فقط** — لم تُجرَ معالجة.

---

## 4. مخاطر انحراف الحدود (Boundary Drift Risks)

### 4.1 مجلدات شبيهة بمنتج خارج النطاق المسموح به في ADR-0001

| المجلد | المحتوى | الخطر |
|---|---|---|
| `mihwar-core/` | خدمة Go (cmd/server، internal/{api,audit,esim,mdm,policy}) | شيفرة منتج — غير مدرج في ADR-0001 |
| `dev-factory/` | سقالة healthcheck + bootstrap | الاسم يستحضر فئة `factory` المحظورة |
| `ios-companion/MihwarCompanion/` | تطبيق Swift كامل | عميل منتج |
| `windows-agent/` | مشروع .NET كامل | عميل منتج |
| `qarar-swarms-sovereign-integration/` | مُثبِّت تراكب يشير إلى مسارات Qarar | يكسر فصل المنتج |
| `sovereign-connectivity-poc/` | monorepo TS (apps/, packages/, dist/) | PoC منتج كامل داخل مستودع مقيد بالحدود |
| `sovereign_network_agent_systemd_v1/` | خدمة systemd | خدمة نظام تشغيلية |

**ملاحظة**: السكربت `adr-0001-boundary-gate.sh` يمر حالياً لأن قائمته الصلبة (`backend_fastapi`، `src/routes`، إلخ) لا تتضمن هذه المسارات. **قرار مطلوب من المالك**: إما توسيع قائمة الحظر وإزالة المجلدات، أو إضافتها صراحةً إلى ADR-0001 كاستثناءات.

### 4.2 `agents/registry.yaml` (تراثي)

CLAUDE.md يَعتبره fallback تلقائي فقط عندما يغيب `.agents/config/agents.yaml`. يجب التأكد من أن المهايئ لا يقرأه عن طريق الخطأ في الإنتاج.

---

## 5. الإجراءات الموصى بها بالترتيب (Recommended Next Actions)

### المرحلة 1 — إصلاحات حاسمة محلية (1–2 يوم)

1. **مزامنة `unifiedAgentAdapter.ts/.js`** ثم `npm test` حتى تمر 30/30.
2. **إصلاح سكربتَي بوابة Python**: `p0-security-test-gate.sh` و`agent-presence-gate.sh`.
3. **التحقق من `npx tsc --noEmit`** — إذا فشل، إصلاح أو إنشاء `src/runners/agentRunner.js` المفقود.
4. **حل ترقيم ADR-0002 المكرر** — إعادة ترقيم أحدهما إلى ADR-0007.

### المرحلة 2 — حسم الحدود (نصف يوم — يحتاج موافقة المالك)

5. اتخاذ قرار حول 7 مجلدات الانحراف (إزالة أو إضافة استثناء في ADR-0001 + توسيع `adr-0001-boundary-gate.sh`).
6. تسوية انحراف PR #176 وفقاً للتدقيق.

### المرحلة 3 — تفعيل وقت التشغيل (يحتاج أسرار)

7. ضبط `BAYYINAH_ENDPOINT`، `MIHWAR_ENDPOINT`، `BAYYINAH_API_TOKEN`، `MIHWAR_API_TOKEN` في GitHub Secrets + Modal.
8. تشغيل `bash scripts/commander/modal-runtime-smoke.sh` ثم `modal deploy .agents/modal_app.py`.
9. ملء أقسام Secrets/Smoke/Edge في `docs/launch-evidence/agent-launch.md` بنتائج موقَّعة.
10. الحصول على Sign-off مشغّل بشري في القسم 8.

### المرحلة 4 — حسم ADR-0004 وبراءات الاختراع (متوسط المدى)

11. اتخاذ قرار حول ADR-0004 (تنفيذ HMAC أم Superseded).
12. سد الفجوات في PAT-001/002/003 أو تحديث ادعاءات البراءات لتعكس الواقع.

---

## 6. ملفات حرجة يجب أن يفتحها المهندس أولاً

1. `CLAUDE.md` — قواعد المستودع.
2. `AGENTS.md` — دليل تشغيل الوكلاء.
3. `docs/decisions/ADR-0001-swarms-boundary.md` — الحدود.
4. `docs/launch-evidence/agent-launch.md` — حالة الإطلاق الحقيقية.
5. `docs/secrets-policy.md` — متطلبات الأسرار.
6. `.agents/skills/codex-commander/SKILL.md` — منظومة التشغيل القائدة.
7. `src/services/unifiedAgentAdapter.ts` و`.js` — موقع إخفاقات الاختبار.
8. `scripts/commander/*.sh` — البوابات (اثنان منها مكسوران).

---

## COMMANDER REPORT

```text
Execution Verdict:
- Status: UNVERIFIED (audit-only)
- Scope: مراجعة شاملة لمستودع CurLexAI/swarms لإعداد تسليم لمهندس مكمِّل
- Canonical Path: docs/operations/engineer-handoff-2026-05-27.md (new)
- Files Touched: docs/operations/engineer-handoff-2026-05-27.md
- Blockers:
   - 8 إخفاقات npm test في unifiedAgentAdapter (P0)
   - service-divergence بين ts/js
   - أسرار وقت تشغيل غير مضبوطة (UNVERIFIED)
   - سكربتان مكسوران: p0-security-test-gate.sh، agent-presence-gate.sh
   - ترقيم ADR-0002 مكرر
   - 7 مجلدات انحراف حدود غير محسومة
- Hot Surface Risk: منخفض (مراجعة فقط، لا تغييرات في الإنتاج)
- What Was Actually Changed: إضافة وثيقة تسليم فقط
- What Was Actually Verified:
   - python3 .agents/validate.py → PASS
   - python3 -m py_compile .agents/*.py → PASS
   - unittest discover → 173 PASS / 2 SKIP
   - npm test:security → 8/8 PASS
   - npm run check:cdn-sri → PASS
   - adr-0001/modal-boundary/qala-egress/public-surface gates → PASS
- What Remains Unverified:
   - npm test (8 إخفاقات)
   - check:service-divergence (FAIL)
   - release-readiness-gate (BLOCK)
   - Modal runtime smoke
   - أسرار GitHub Actions/Modal/Render/Cloudflare
   - Sign-off مشغّل بشري
- Next Valid Action: المهندس المكمِّل يبدأ من §5 المرحلة 1 — مزامنة unifiedAgentAdapter
```
