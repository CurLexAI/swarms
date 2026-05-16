# Domain: Sovereign Legal AI

**النطاق:** خطوط البيانات القانونية السيادية، استيعاب SAMA/PDPL/NCA، التحليل القانوني العربي
**الحالة:** طبقة سيادية خاصة — تعمل داخل Modal فقط

---

## المبدأ الجوهري

خطوط البيانات القانونية السيادية تبقى داخل الطبقة الخاصة لـ Modal/Qdrant.
لا تُنشئ سطحاً عاماً أو REST API لأي بيانات قانونية سيادية.

---

## ما هو مسموح في هذا النطاق

داخل الطبقة السيادية لـ Modal:

1. استيعاب المستندات القانونية (ingestion)
2. التضمين والبحث المتجه (embedding + vector search)
3. التحليل القانوني عبر نماذج مُعتمدة
4. تسجيل audit trail لكل عملية

---

## ما هو محظور

- إنشاء REST/GraphQL API عامة لبيانات قانونية
- رفع نصوص قانونية لخدمات AI خارجية غير مُعتمدة
- تخزين بيانات قانونية خارج البنية التحتية السيادية
- ادعاء امتثال SAMA/PDPL/NCA بدون دليل مستشهد

---

## توجيه النماذج للمهام القانونية

```python
# من model_policy_engine.py
if profile.requires_arabic_legal_precision:
    return ModelRoute(
        provider="anthropic",
        model="claude-opus-or-sonnet-current",
        reason="دقة قانونية عربية تتطلب نموذجاً بسياق طويل + Bayyinah validation",
        requires_reviewer=True,
        reviewer_agent_id="bayyinah",
    )
```

---

## متطلبات Audit Trail

كل عملية على بيانات قانونية سيادية تتطلب:

```
- timestamp
- agent_id
- operation_type
- data_classification
- reviewer_id (إذا كانت Bayyinah مطلوبة)
- verdict
```

المرجع: `src/services/AuditService.ts` + `src/utils/auditLogger`

---

## ملاحظة الامتثال

لا ادعاء امتثال تنظيمي دون دليل مستشهد.
هذا الملف يصف القدرات التقنية فقط، لا الامتثال القانوني.
