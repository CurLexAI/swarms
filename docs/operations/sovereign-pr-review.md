# 🛡️ المراجعة السيادية للـ Pull Requests

## نظرة عامة

نظام **Sovereign PR Review** هو آلية مراجعة آلية محلية بالكامل، **بدون أي اتصال خارجي** (لا Modal، لا OpenAI، لا Anthropic).

## المعمارية

```
┌─────────────────────────────────────┐
│   GitHub PR opened/edited/synced    │
└──────────────┬──────────────────────┘
               ↓
┌──────────────────────────────────────┐
│  .github/workflows/agent-review.yml  │
│  (CI/CD trigger)                     │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│  .agents/pr_review.py                │
│  (Sovereign Reviewer)                │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│  Local checks:                       │
│  • Secrets detection                 │
│  • Hardcoded URLs (Modal)            │
│  • Destructive operations           │
│  • Code quality                      │
└──────────────────────────────────────┘
```

## التشغيل

### مراجعة محلية
```bash
python .agents/pr_review.py --pr-number 42 --diff-file diff.txt
```

### صيغ الإخراج

| الصيغة | الوصف |
|--------|------|
| `json` | تقرير JSON كامل (افتراضي) |
| `github` | تعليق GitHub Markdown |
| `console` | ملخص نصي للـ Terminal |

## القواعد

### 1. كشف الأسرار (CRITICAL)
- `sk-<redacted>` (OpenAI)
- `ghp_*` (GitHub PAT)
- `AKIA*` (AWS)
- `AIza*` (Google)
- hardcoded password assignments
- hardcoded API key assignments

### 2. كشف Modal URLs (HIGH)
- أي رابط ينتهي بنطاق Modal runtime
- أي رابط يحتوي على اسم function داخل نطاق Modal runtime

### 3. العمليات المدمرة (CRITICAL)
- remove-root style shell commands
- drop-database style SQL commands
- unbounded table delete commands

### 4. جودة الكود (INFO)
- TODO/XXX في نفس السطر
- TODO دون تحديد موعد

## النتائج

- ✅ **APPROVE** = لا مشاكل
- 🛑 **REQUEST_CHANGES** = مشاكل CRITICAL أو HIGH

## الاختبارات

```bash
python -m pytest -q tests/test_pr_review_modal_relay.py
```

## الأمان

- ✅ لا يستدعي أي API خارجي
- ✅ لا يرسل الكود لأي خادم
- ✅ يعمل بالكامل داخل CI
- ✅ يكتشف الأسرار قبل التسريب

## استكشاف الأخطاء

### الخطأ: "Module not found"
```bash
# تأكد من وجود pr_review.py في .agents/
ls -la .agents/pr_review.py
```

### الخطأ: "Permission denied"
```bash
chmod +x .agents/pr_review.py
```
