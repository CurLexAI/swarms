# Mode: Executor

**يُفعَّل عند:** تنفيذ مهمة محددة، تطبيق patch، إنشاء ملف، تشغيل بوابات
**الوكيل الأساسي:** Copilot SWE (scaffold) أو Mihwar (تنفيذ معقد)

---

## التوجه

أصغر تغيير إنتاجي كامل وصحيح. لا تُضف ما لم يُطلب.

---

## قواعد التنفيذ

1. **لا تتجاوز النطاق** — عدّل فقط الملفات المحددة في Scope Lock
2. **لا تُضف معالجة أخطاء لسيناريوهات مستحيلة** — ثق بضمانات الإطار
3. **لا تُعلّق ما يشرح نفسه** — الأسماء الجيدة تكفي
4. **لا تُنشئ ملفات توثيق** — إلا إذا طُلب صراحةً
5. **الأسطح الساخنة أولاً** — تحقق من base branch والتغييرات النشطة

---

## قبل كل تعديل

```bash
# تحقق من الحالة
git status
git diff --stat

# اقرأ الملف الهدف قبل التعديل
# استخدم Read tool — لا cat
```

---

## بعد كل تعديل

```bash
# تحقق من بنية Python
python3 -m py_compile <file>.py

# تحقق من TypeScript
npx tsc --noEmit

# نفّذ الاختبارات ذات الصلة
python3 -m pytest -q tests/<relevant_test>.py
npm test
```

---

## بوابات ما قبل الادعاء بالجاهزية

```bash
bash scripts/commander/p0-security-test-gate.sh .
bash scripts/commander/modal-boundary-gate.sh .
bash scripts/commander/adr-0001-boundary-gate.sh .
bash scripts/commander/agent-presence-gate.sh .
```

---

## حدود Copilot SWE

```yaml
scaffold_only: true
deploy_authority: false
reads_secrets: false
may_modify_workflows: false
may_merge: false
paired_review_required: true  # with Bayyinah
```
