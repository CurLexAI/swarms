# Agent Profile: Security Audit Agent

**المكوّن:** `src/security/sovereignCyberRadar.ts`
**الحالة:** أداة CLI آلية، لا وكيل LLM مستقل

---

## الغرض

فحص أمني متخصص للكود والبنية التحتية في منظومة CurLexAI.
يعمل كطبقة إضافية فوق مراجعة Bayyinah.

---

## تشغيل الفحص الأمني

```bash
npm run security:radar:scan    # فحص شامل
npm run security:radar:report  # تقرير تفصيلي
```

---

## نطاق الفحص

### P0 Security Gate

```bash
bash scripts/commander/p0-security-test-gate.sh .
```

يتحقق من:
- وجود secrets في الكود
- انتهاكات Modal boundary
- XSS / SQL Injection / OWASP Top 10
- Prompt injection surfaces
- Dynamic URL construction من مدخلات غير موثوقة

---

## مستويات النتائج

| المستوى | الإجراء |
|---|---|
| CRITICAL | أوقف كل شيء — لا تمر بوابة |
| HIGH | لا دمج دون حل |
| MEDIUM | يُحل قبل الدمج العام |
| LOW | يوثَّق ويُتابَع |
| INFO | للمعلومات فقط |

---

## الاختبارات الأمنية

```bash
# اختبارات الأمان P0
python3 -m pytest -q tests/test_bayyinah_validation_gate.py
npm run test:security    # sovereignCyberRadar tests
```

---

## ملفات TS/JS المترافقة

هذه الملفات موجودة بنسختين (`.ts` + `.js`) ويجب أن تبقى متزامنة:

```
src/security/sovereignCyberRadar.ts
src/services/unifiedAgentAdapter.ts
src/services/AuditService.ts
src/utils/auditLogger
```

يكتشف `scripts/check-service-divergence.mjs` التباعد تلقائياً.

```bash
npm run check    # يشمل فحص التباعد
```
