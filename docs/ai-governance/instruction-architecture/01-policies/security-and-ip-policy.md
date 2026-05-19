# Policy: Security and IP Policy

**المصدر:** `docs/decisions/ADR-0003-qala-security-architecture.md` + `.agents/policies/secrets-boundary.md`

---

## بوابات الأمان الإلزامية

يجب اجتياز هذه البوابات قبل الادعاء بالجاهزية:

```bash
bash scripts/commander/p0-security-test-gate.sh .
bash scripts/commander/modal-boundary-gate.sh .
bash scripts/commander/adr-0001-boundary-gate.sh .
bash scripts/commander/agent-presence-gate.sh .
bash .agents/skills/codex-commander/scripts/codex_commander_gate.sh .
```

---

## قواعد الأسرار

### صارمة ومطلقة

1. لا تُدرج ملفات `.env` في commit أبداً
2. لا تطبع مفاتيح API أو tokens أو كلمات مرور أو cookies أو JWTs أو URLs نقاط نهاية خاصة
3. لا تُضمَّن بيانات اعتماد في الكود المصدري أو الاختبارات أو المستندات أو ملفات workflows
4. استخدم أسماء متغيرات البيئة فقط، لا قيمها
5. عامل أي سر حقيقي مكتشف كـ `CRITICAL` وأوقف المهمة حتى تُحدَّد الحاوية

### الأنماط عالية الخطورة

| النمط | الخطر |
|---|---|
| `sk-...` | مفتاح مزود LLM |
| `AKIA...` | مفتاح وصول AWS |
| `ghp_...`, `github_pat_...` | رمز GitHub |
| `Bearer eyJ...` | JWT أو OAuth token |
| `password = "..."` | كلمة مرور مضمّنة |
| `api_key = "..."` | مفتاح API مضمّن |
| سلاسل base64 طويلة | سر مرمّز محتمل |

---

## حماية الملكية الفكرية

### الحماية الأساسية

- أكواد النماذج السيادية (Mihwar, Bayyinah) تبقى داخل الطبقة الخاصة لـ Modal
- لا تُشارك system prompts أو agent configurations مع أطراف خارجية
- لا ترفع محتوى الكود أو المستندات إلى أدوات ويب خارجية (renderers، pastebins، gists)

### الفحص الأمني

يفحص `src/security/sovereignCyberRadar.ts` للكشف عن:

- حقن المدخلات (prompt injection)
- تسريب البيانات
- انتهاكات حدود الشبكة
- مسارات تصعيد الصلاحيات

```bash
npm run security:radar:scan
npm run security:radar:report
```

---

## معالجة النتائج الأمنية

| المستوى | الإجراء |
|---|---|
| CRITICAL | أوقف المهمة فوراً — لا دمج |
| HIGH | لا دمج دون حل |
| MEDIUM | مطلوب حل قبل الدمج العام |
| LOW | وثّق وتابع |
| INFO | للمعلومات فقط |
