# SR.BSM Command Interface — Mock-Only Handoff & Claim Correction — 2026-05-29

> وثيقة تسليم وتصحيح قيادي. تُصحّح الادعاء السابق (`VERIFIED & LIVE`) إلى `UI_SMOKE_VERIFIED`،
> وتُحدّد المرحلة القادمة كواجهة أوامر **محاكاة فقط (mock-only)** بلا أي إرسال خارجي، مع شروط
> البوابة الأمنية الواجب إثباتها قبل أي توجيه أوامر حي. تُبنى على نفس حدود
> `docs/operations/sr-bsm-dashboard-bff-handoff-2026-05-29.md` (PR #254).

---

## Execution Verdict

- Status: `BLOCKED` for direct SR.BSM source modification; `CHANGED_BUT_NOT_VERIFIED` for this CurLexAI/swarms handoff record.
- Scope: تصحيح صياغة الادعاء، وتسليم عقد تنفيذ مُشدَّد لواجهة أوامر **محاكاة فقط** داخل SR.BSM (لا Modal، لا إرسال خارجي).
- Canonical Path: Browser Dashboard -> SR.BSM Next.js BFF (`/api/command`, mock) -> (مستقبلاً) Qarar Security Gate -> Mihwar Gateway -> Modal vLLM backend.
- Files Touched: `docs/operations/sr-bsm-command-interface-mock-handoff-2026-05-29.md`.
- Blockers: `AUTH_MISSING` — مستودع `moteb1989/SR.BSM` غير قابل للوصول من هذا الـ worktree؛ نطاق أدوات GitHub مقيّد بـ `curlexai/swarms`. كما أن `src/api/` مسار محظور صراحةً في `scripts/commander/adr-0001-boundary-gate.sh`، فلا يجوز إنشاء ملفات منتج Next.js داخل هذا المستودع.
- Hot Surface Risk: عالٍ — صندوق الأوامر يحوّل الواجهة من read-only إلى **action surface**. السطوح الساخنة: `/api/command`, CSP، مصادقة Render، أي بيانات اعتماد بوابة.
- What Was Actually Changed: إضافة هذه الوثيقة فقط. لم تُعدَّل أي شيفرة منتج، ولم تُلمَس أي واجهة حية.
- What Was Actually Verified: `src/api` مؤكَّد كمسار محظور في بوابة ADR-0001 (سطر 24). PR #254 يُصرّح أن تعديل SR.BSM `BLOCKED` لانعدام الوصول.
- What Remains Unverified: مصدر SR.BSM، lint/tsc/build داخل SR.BSM، صحة الواجهة الحية، اتصال Modal، توجيه الأوامر الحي. لا يوجد healthcheck يثبت أن الوكلاء "active".
- Next Valid Action: تنفيذ العقد أدناه داخل مستودع SR.BSM (بوصول مستودعي)، ثم `npm run lint`, `npx tsc --noEmit`, `npm run build`.

---

## 1. التصحيح القيادي للادعاء (Claim Correction)

الادعاء `VERIFIED & LIVE` **مرفوض**. الصياغة الدقيقة هي `UI_SMOKE_VERIFIED`:

> الواجهة تعرض قائمة وكلاء ثابتة أو محمية عبر `/api/agents`. هذا إنجاز حقيقي، لكنه **ليس** دليلاً
> على أن الوكلاء الحيين في swarms/Modal متصلون فعلياً أو أن أوامرهم تعمل end-to-end.

الفرق بين ما هو مقبول وما هو غير مثبت:

| الادعاء | الحكم |
|---|---|
| Dashboard يعرض وكلاء | مقبول — إذا رُئي في الواجهة (`UI_SMOKE_VERIFIED`) |
| `/api/agents` يعمل | مقبول — إذا أعاد JSON أو 401 مقصود (`VERIFIED` في PR #254: أعاد 401) |
| الوكلاء `Active` فعلياً | **غير مثبت** — لا يوجد healthcheck |
| Modal متصل بالـ Dashboard | **غير مثبت** |
| Command routing جاهز | **غير جاهز** |

**الصياغة المعتمدة:** «المرحلة الأولى من *تمثيل* الوكلاء في الواجهة اكتملت. الربط الحي بالمصنع لا يزال غير مثبت.»

يُمنع كتابة `Dynamic Command Routing` أو `Live Modal Bridge` في عنوان أو وصف أي PR قبل وجود بوابة أمنية حقيقية واختبار end-to-end.

---

## 2. لماذا هذا تسليم وليس تنفيذاً مباشراً هنا (Boundary Note)

1. `AUTH_MISSING`: مستودع SR.BSM غير متاح من بيئة التنفيذ الحالية (نطاق مقيّد بـ `curlexai/swarms`).
2. `BOUNDARY`: `src/api/` و`src/routes/` مساران محظوران في `adr-0001-boundary-gate.sh`. إنشاء `src/app/api/command/route.ts` أو مكوّنات Next.js داخل `swarms` سيُفشل البوابة ويُعدّ انحراف حدود.

لذلك الناتج الصحيح والمنضبط هو **عقد تنفيذ + تصحيح ادعاء** يُطبَّق داخل SR.BSM، تماماً كنمط PR #254.

---

## 3. القرار: المرحلة القادمة = Mock Command Interface — No External Dispatch

ليست `Dynamic Command Routing`. واجهة الأوامر المحاكاة هي اختبار دخان للواجهة والـ BFF فقط:
لا Modal، لا APIs خارجية، لا توكنات، same-origin فقط.

### العقد المُشدَّد للوكيل في SR.BSM

```text
You are working in the SR.BSM Next.js repository.
Objective:
Add a secure mock-only Command Interface to the Swarms Dashboard.
This is NOT live agent execution.
This is NOT Modal dispatch.
This is a UI and BFF smoke test only.
Rules:
- Do not call Modal.
- Do not call external AI APIs.
- Do not expose tokens.
- Do not use NEXT_PUBLIC_* for secrets.
- Do not store raw command text in logs.
- Do not claim agents are active/live unless real healthchecks exist.
- All browser requests must be same-origin only.
- The frontend may POST only to /api/command.
- /api/command must return a mock Aegis validation response.
- Use strict TypeScript.
- Do not use any.
Tasks:
1. Add a component:
   src/components/CommandInterface.tsx
2. The component must include:
   - textarea for command input
   - selected target agent dropdown or fixed target = "aegis-security-swarm"
   - "Send to Nexus" button
   - loading state
   - error state
   - response panel
   - max client-side input length: 2000 characters
3. Update:
   src/components/SwarmsDashboard.tsx
   Add CommandInterface below the agents list.
4. Add API route:
   If App Router:
   src/app/api/command/route.ts
   If Pages Router:
   src/pages/api/command.ts
   Do not create both unless the project already uses both.
5. /api/command requirements:
   - accept POST only
   - reject non-JSON requests
   - validate body as unknown
   - require command: string
   - trim command
   - reject empty command
   - reject command > 2000 chars
   - classify command as PUBLIC_MOCK only
   - return 400 for invalid input
   - return 405 for unsupported method if Pages Router
   - return no-store headers
   - do not call external URLs
   - do not import Modal SDK
   - do not read secrets
   - do not log raw command
6. Response shape:
   {
     "status": "received",
     "mode": "mock",
     "agent": "aegis-security-swarm",
     "classification": "PUBLIC_MOCK",
     "message": "Command verified by mock Aegis firewall. Live Modal bridge is not enabled.",
     "commandHash": "<sha256 hash of command>",
     "next": "Awaiting Security Gate / Mihwar live bridge."
   }
7. Add tests if the repo has a test framework:
   - rejects empty command
   - rejects long command
   - returns mock response
   - does not expose external URL or token
8. Run:
   npm run lint
   npx tsc --noEmit
   npm run build
Return:
- changed files
- diff summary
- command outputs
- whether this is mock-only or live
- remaining blockers before live command routing
Commit message:
feat: add secure mock command interface
```

---

## 4. عقد استجابة `/api/command` (Mock Response Shape)

استجابة المحاكاة لا تحتوي نصاً خاماً ولا توكنات — فقط hash + metadata:

```json
{
  "status": "received",
  "mode": "mock",
  "agent": "aegis-security-swarm",
  "classification": "PUBLIC_MOCK",
  "message": "Command verified by mock Aegis firewall. Live Modal bridge is not enabled.",
  "commandHash": "<sha256 hash of command>",
  "next": "Awaiting Security Gate / Mihwar live bridge."
}
```

السلوك الإلزامي للمسار:

- POST فقط؛ أي method آخر → 405 (Pages Router) أو رفض صريح.
- يرفض الطلبات غير JSON؛ يتحقق من الجسم كـ `unknown`.
- `command: string` مطلوب، يُقصّ (trim)، يُرفض الفارغ، يُرفض ما يتجاوز 2000 حرف → 400.
- `Cache-Control: no-store`.
- لا استدعاء URLs خارجية، لا استيراد Modal SDK، لا قراءة أسرار، لا تسجيل النص الخام.
- التصنيف `PUBLIC_MOCK` فقط.

---

## 5. شروط البوابة قبل أي Live Command Routing (Gate Preconditions)

لا انتقال إلى توجيه الأوامر الحقيقي حتى تُثبَت الأربعة (label إلزامي لكل بند):

1. `/api/command` محمي بمصادقة، أو على الأقل same-origin + CSRF/rate limit. — حالياً `NOT_STARTED`.
2. CSP لا يسمح للمتصفح بالاتصال المباشر بـ `*.modal.run`. — حالياً `HOLD` (PR #254 أثبت أن CSP لا يزال يسمح بـ `https://*.modal.run`).
3. وجود Qarar Security Gate يستقبل الأمر ويفحصه قبل Modal. — حالياً `NOT_STARTED`.
4. وجود audit event يسجّل `hash + metadata` لا النص الخام. — حالياً `NOT_STARTED`.

---

## 6. معايير القبول (Acceptance Criteria — تُتحقَّق داخل SR.BSM)

- `VERIFIED`: `src/components/CommandInterface.tsx` يحوي textarea, target ثابت/قائمة, زر "Send to Nexus", loading/error/response states, حدّ 2000 حرف على العميل.
- `VERIFIED`: `SwarmsDashboard.tsx` يعرض `CommandInterface` أسفل قائمة الوكلاء.
- `VERIFIED`: المتصفح يرسل POST إلى `/api/command` same-origin فقط؛ لا مرجع لـ Modal URL/SDK/token في أي شيفرة أمامية.
- `VERIFIED`: `/api/command` يرفض الفارغ والطويل (>2000)، ويعيد 400 للمدخل غير الصالح، وlا يسجّل نصاً خاماً، ويعيد no-store.
- `VERIFIED`: الاستجابة تطابق الشكل في §4 وتُصنَّف `PUBLIC_MOCK`، والرسالة تُصرّح صراحةً أن الجسر الحي غير مُفعَّل.
- `VERIFIED`: `npm run lint`, `npx tsc --noEmit`, `npm run build` تمر داخل SR.BSM.
- `VERIFIED`: لا `eslint.ignoreDuringBuilds = true` ولا `typescript.ignoreBuildErrors = true` كحل دائم.

---

## COMMANDER REPORT

```text
Execution Verdict:
- Status: BLOCKED (SR.BSM source) / CHANGED_BUT_NOT_VERIFIED (swarms handoff)
- Scope: تصحيح ادعاء VERIFIED&LIVE -> UI_SMOKE_VERIFIED + عقد واجهة أوامر mock-only لـ SR.BSM
- Canonical Path: docs/operations/sr-bsm-command-interface-mock-handoff-2026-05-29.md (new)
- Files Touched: docs/operations/sr-bsm-command-interface-mock-handoff-2026-05-29.md
- Blockers:
   - AUTH_MISSING: مستودع SR.BSM غير متاح (نطاق مقيّد بـ curlexai/swarms)
   - BOUNDARY: src/api/ محظور في adr-0001-boundary-gate.sh — لا يجوز إنشاء مسار Next.js هنا
   - CSP لا يزال يسمح بـ *.modal.run في المتصفح (من PR #254) — HOLD قبل live routing
- Hot Surface Risk: عالٍ — صندوق الأوامر يحوّل الواجهة إلى action surface
- What Was Actually Changed: إضافة وثيقة تسليم وتصحيح ادعاء فقط
- What Was Actually Verified:
   - src/api مسار محظور في adr-0001-boundary-gate.sh (سطر 24)
   - PR #254 يُصرّح بأن تعديل SR.BSM BLOCKED لانعدام الوصول
- What Remains Unverified:
   - مصدر SR.BSM، lint/tsc/build داخل SR.BSM
   - صحة الواجهة الحية / اتصال Modal / صحة الوكلاء (لا healthcheck)
   - الشروط الأربعة لبوابة ما قبل live routing
- Next Valid Action: تنفيذ العقد داخل SR.BSM بوصول مستودعي ثم lint/tsc/build
```
