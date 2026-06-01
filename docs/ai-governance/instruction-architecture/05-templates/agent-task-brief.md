# Template: Agent Task Brief

استخدم هذا القالب عند تكليف أي وكيل بمهمة جديدة.

---

## قالب Task Brief

```markdown
## Task Brief — [عنوان المهمة]

**التاريخ:** YYYY-MM-DD
**الوكيل المُكلَّف:** [ ] Mihwar  [ ] Bayyinah  [ ] Copilot SWE
**المُراجع:** [ ] Bayyinah  [ ] Human  [ ] N/A
**الفرع:** `feature/xxx` أو `fix/xxx`

---

### الهدف

[وصف واضح وموجز للنتيجة المطلوبة]

### النطاق

**الملفات المسموح تعديلها:**
- `path/to/file1.ts`
- `path/to/file2.py`

**خارج النطاق (لا تمس):**
- `.github/workflows/`
- `scripts/commander/*.sh`
- [غيرها]

### معايير القبول

- [ ] الاختبارات تمر: `python3 -m pytest -q tests/`
- [ ] TypeScript: `npx tsc --noEmit` (بدون أخطاء جديدة)
- [ ] بوابات المستودع تمر
- [ ] لا CRITICAL/HIGH من Bayyinah

### مسار التراجع

[كيف نتراجع إذا فشل التطبيق؟]

### الحدود

- لا تُعدِّل ملفات الحوكمة
- لا تُضف تبعيات بدون موافقة
- لا تنشر production بدون موافقة صريحة

### الأسرار المطلوبة

- `MIHWAR_ENDPOINT`: [ ] SET  [ ] UNSET
- `BAYYINAH_ENDPOINT`: [ ] SET  [ ] UNSET
- `AGENT_API_TOKEN`: [ ] SET  [ ] UNSET
```

---

## مثال مملوء

```markdown
## Task Brief — إضافة rate limiting لبوابة الاستيعاب

**التاريخ:** 2026-05-16
**الوكيل المُكلَّف:** [x] Mihwar
**المُراجع:** [x] Bayyinah
**الفرع:** `feature/ingest-rate-limiting`

### الهدف
إضافة rate limiting (100 طلب/دقيقة) لنقطة نهاية الاستيعاب في Modal.

### النطاق
**مسموح:** `.agents/modal_app.py`، `tests/test_ingest_rate_limit.py`
**ممنوع:** أي شيء خارج ما ذُكر

### معايير القبول
- [ ] اختبار rate limiting يمر
- [ ] لا تراجع في اختبارات P0
- [ ] Bayyinah تُقر: لا CRITICAL/HIGH
```
