# Policy: Execution and Approval Policy

**المصدر:** `.agents/policies/execution-discipline-maximum.md` + `AGENTS.md`

---

## قيم الحالة النهائية المسموحة

```
VERIFIED_FIXED
PARTIALLY_APPLIED
CHANGED_BUT_NOT_VERIFIED
BLOCKED
UNVERIFIED
NOT_STARTED
SUPERSEDED
CONFLICTED
```

لا تستخدم قيماً خارج هذه القائمة. لا تُدمج SKIPPED مع PASS.

---

## ترتيب التنفيذ الإلزامي

```
1. Scope Lock      — حدد المهمة والملفات المسموح تعديلها والإجراءات الممنوعة
2. Discovery       — افحص المستودع قبل أي تعديل
3. Policy Check    — طبّق سياسات الأسرار والشبكة وسلامة التبعيات
4. Safe Edit Plan  — وضّح ما سيتغير وما لن يتغير
5. Implementation  — أصغر تغيير إنتاجي كامل وصحيح
6. Validation      — نفّذ الفحوصات الثابتة والاختبارات أو وضّح العوائق
7. Report          — استخدم قالب التقرير المعياري
```

---

## تصنيف العوائق

عند الحظر، صنّف العائق باستخدام أحد هذه القيم:

```
AUTH_MISSING
AUTH_INVALID
AUTH_EXPIRED
CONFIG_NOT_FOUND
SYNTAX_FAILURE
TYPE_FAILURE
TEST_FAILURE
RUNTIME_FAILURE
WORKFLOW_CONFLICT
HOT_SURFACE_CONFLICT
SECRET_MISSING
DEPLOYMENT_BLOCKED
UNVERIFIED_RUNTIME
```

لا تكرر نفس الإجراء الفاشل بعد تأكيد العائق.

---

## انضباط الأسطح الساخنة

تُعامَل هذه العناصر كأسطح ساخنة:

- المحوّلات المشتركة (unifiedAgentAdapter)
- مسارات النشر
- ملفات العقود (API contracts)
- مسارات المصادقة
- Workflow files

القواعد:
- لا تفتح مسارات تنفيذ متوازية على نفس السطح الساخن
- راجع الفرع الأساسي والتغييرات النشطة قبل البدء أو إعادة فتح العمل على سطح ساخن

---

## بروتوكول التعاون بين الوكلاء

```
الافتراضي: Mihwar يُنشئ → Bayyinah تراجع → حتى 3 دورات تعديل → موافقة بشرية
```

| الشرط | الحكم |
|---|---|
| نتائج CRITICAL/HIGH غير محلولة | لا دمج |
| أكثر من 3 دورات تعديل | تصعيد إلى مراجعة بشرية |
| تغييرات `.github/workflows/` | مراجعة بشرية مطلوبة |
| تغييرات CODEOWNERS | مراجعة بشرية مطلوبة |
| إضافة/حذف تبعيات | مراجعة بشرية قبل الدمج |

---

## إجراءات تتطلب موافقة صريحة من المستخدم

- الدمج (merge)
- Force push
- نشر production
- تدوير الأسرار
- تعديل الفواتير
- حذف ملفات الحوكمة
- تجاوز سياسة أي بوابة
