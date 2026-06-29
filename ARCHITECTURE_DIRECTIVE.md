# Architecture Directive
## العقيدة المعمارية لمنصة الذكاء الاصطناعي

**الغرض:** تحديد عقيدة معمارية قطعية وواضحة لمنصة الذكاء الاصطناعي، مع فصل صارم بين طبقات النواة، طبقة التحكم، وواجهة الجمهور، وتحديد خرائط الأسراب والوكلاء، وضوابط الامتثال والأمن المتوافقة مع المتطلبات السعودية.

---

## 1) Core Architecture (البنية الأساسية)

### Bayyinah (النواة ومحرك الأدلة)

**الوصف:**
النواة والمحرك الأساسي: نموذج المعرفة، محرك الأدلة، ومستودع الحقيقة (Single Source of Truth) المدعوم بـ Qdrant وطبقات تخزين/فهرسة مرتبطة.

**قواعد أساسية:**
1. كل قرار أو استنتاج يعتمد على استرجاع أدلة من Bayyinah.
2. لا يُسمح بتعديل بيانات Bayyinah إلا عبر بوابة تفويض رسمية في Mihwar.
3. عمليات القراءة تخضع لسياسات الوصول (RBAC) وتدقيق كامل (audit logs).

### Mihwar (طبقة التحكم والتدقيق)

**الوصف:**
طبقة التحكم والغلاف الإداري والأمني. تدير دورة حياة الوكلاء، التوجيه، بوابات الامتثال، وسياسات الوصول.

**قواعد أساسية:**
1. كل تفاعل بين Qarar وBayyinah يمر حصراً عبر Mihwar.
2. Mihwar يطبّق بوابات الامتثال (ECC-2:2024, PDPL) ويمتلك آليات التصديق، التفويض، والتدقيق.
3. لا تُنفّذ أي أوامر تنفيذية على البنية التحتية أو قواعد البيانات دون مرور سياسات Mihwar.

### Qarar (واجهة الجمهور)

**الوصف:**
واجهة الجمهور والنماذج النهائية التي تتفاعل مع المستخدمين.

**قواعد أساسية:**
1. Qarar لا يتصل مباشرةً بـ Bayyinah.
2. كل مخرجات Qarar يجب أن تحمل أثر (provenance) واضحاً يبيّن الأدلة المستدعاة من Bayyinah عبر Mihwar.
3. Qarar يعرض مخرجات قابلة للمراجعة البشرية عند وجود حالات تصعيد أو حساسية.

---

## 2) Swarms & Agents Mapping (SYSTEM INVENTORY)

> **ملاحظة:** جميع الكيانات التالية تخضع للعقيدة المعمارية وتُدار حصراً عبر Mihwar.

| الكيان | النوع | المسؤولية الأساسية |
|---|---|---|
| Free Birds | Custom Swarm | مهام تنفيذية عامة؛ يعمل كعامل Worker تحت Mihwar |
| Wolf | Custom Swarm | مهام تحليلية/استكشافية؛ يعمل تحت Mihwar |
| Sonar | Custom Swarm | مراقبة/رصد؛ يعمل تحت Mihwar |
| sama-swarm | CLI/SOP Swarm | تغذية البيانات (Ingest) إلى Bayyinah |
| falcon-pulse | CLI/SOP Swarm | تنفيذ مهام مجدولة من `seed_tasks.json` |
| Bayyinah evidence swarm | Core Swarm | استرجاع الأدلة والتعامل مع Qdrant & BGE-M3 |
| Mihwar control swarm | Core Swarm | تطبيق بوابات الامتثال وإدارة دورة حياة الوكلاء |
| Qarar drafting swarm | Core Swarm | صياغة المخرجات النهائية لواجهة الجمهور |
| Repo Agent | Micro-Agent | مراقبة المستودع وتطبيق التعديلات البرمجية |
| search_agent | Micro-Agent | سحب/معالجة البيانات ورفعها إلى Qdrant |
| issue-classifier | Micro-Agent | تصنيف القضايا والمهام |
| evidence-retriever | Micro-Agent | استرجاع الأدلة من Bayyinah |
| conflict-checker | Micro-Agent | فحص التعارضات بين الأدلة/السياسات |
| control-mapper | Micro-Agent | ترجمة متطلبات ECC-2/PDPL إلى ضوابط تنفيذية |
| draft-writer | Micro-Agent | كتابة المسودات والـ ADRs |
| citation-validator | Micro-Agent | التحقق من صحة الاستشهادات والمراجع |
| escalation-gate | Micro-Agent | بوابة التصعيد البشري والتحقق النهائي |

---

## 3) Operational Rules (قواعد تشغيلية ملزمة)

1. **حتمية المرور عبر Mihwar:** لا يُسمح لأي Swarm أو Agent بالتواصل المباشر مع Qarar أو Bayyinah دون توجيه وتصديق من Mihwar.
2. **فصل الصلاحيات:** تفويضات الكتابة إلى Bayyinah تُمنح فقط بعد مراجعة تلقائية وبشرية عبر بوابة التفويض في Mihwar.
3. **سير العمل المتسلسل:** إطلاق مهام تؤثر على بنية البيانات أو سياسات الأمان يجب أن يتبع مسار:
   `Plan → Review (Mihwar) → Test (sandbox) → Approve → Deploy`.
4. **حدود الوكلاء:** وكلاء التنفيذ (Workers) لا يوسّعون نطاق المهمة من تلقاء أنفسهم؛ أي اقتراح توسيع يجب أن يُرفع كـ issue إلى Mihwar.
5. **التدقيق والتتبّع:** كل عملية قراءة/كتابة/تنفيذ تُسجّل مع metadata تشمل:
   `agent-id, swarm-id, request-id, evidence-refs, timestamp`.
6. **التصعيد البشري:** حالات الثقة المنخفضة أو التعارضات أو التغييرات على قواعد البيانات تتطلب مروراً عبر `escalation-gate` قبل الدمج.

---

## 4) Security & Compliance Mapping

### PDPL (قانون حماية البيانات السعودي)

- تصنيف البيانات الحساسة داخل Bayyinah.
- تشفير بيانات الراحة والنقل.
- سجلات وصول مفصّلة واحتفاظ بسجلات الوصول وفق متطلبات PDPL.

### ECC-2:2024 (ضوابط الامتثال السيبراني)

- `control-mapper` يترجم متطلبات ECC إلى قواعد تنفيذية داخل Mihwar.
- بوابات الامتثال تمنع نشر أي نموذج أو وكيل قبل اجتياز فحوص ECC.

### NCA / الجهات التنظيمية

- آليات تقارير دورية (audit reports) وواجهات للتدقيق الخارجي.

### Network Boundary (حدود الشبكة)

- الأسراب لا تتصل بالإنترنت العام مباشرةً؛ كل حركة خارجية تمر عبر بوابة مصادقة ومراقبة في Mihwar.

---

## 5) Onboarding Checklist (لكل كيان جديد)

- [ ] استلام وقراءة `architecture_directive.md`.
- [ ] تسجيل الهوية التشغيلية (`agent-id`, `swarm-id`) في سجل Mihwar.
- [ ] تهيئة مفاتيح الوصول المؤقتة (short-lived credentials) عبر بوابة Mihwar.
- [ ] تنفيذ اختبار sandbox لعمليات القراءة فقط.
- [ ] توقيع اتفاقية تشغيل (Operational SLA) والالتزام بسياسات PDPL/ECC.
- [ ] تفعيل logging وtracing قبل أي عملية كتابة.

---

## 6) Templates: System Message للوكيل

**System message (Agent bootstrap):**

أنت وكيل تشغيلي مُصرّح له بالعمل ضمن Swarm: `<SWARM_NAME>`.

- اقرأ `architecture_directive.md`.
- كل طلب تنفيذ يمر عبر Mihwar.
- لا تتصل مباشرةً بـ Bayyinah أو Qarar.
- سجّل كل نشاط مع evidence refs.
- عند شك أو تعارض، استدعِ `escalation-gate`.

**Acknowledgment phrase:**
`"علم وتم تحديث السياق المعماري"`

> **ملاحظة:** العبارة أعلاه مخصّصة لوكلاء داخل النظام ليستخدموها كإقرار تشغيلي؛ لا تُستخدم كدليل على أن أي طرف خارجي أو مساعد خارجي قد غيّر ذاكرته أو صلاحياته.

---

## 7) Governance & CI/CD Hooks (توصيات تنفيذية)

1. **Pre-merge checks (GitHub Actions):** أي PR يغيّر قواعد Bayyinah أو سياسات Mihwar يجب أن يتضمن:
   - ADR
   - test results (sandbox)
   - evidence refs
   - approval from Mihwar approvers

2. **Automated Policy Gate:**
   Action يطلب توقيع Mihwar قبل الدمج.

3. **Audit Export:**
   كل أسبوع تُصدّر سجلات التدقيق إلى مخزن مؤمن للامتثال.

---

## ⚠️ Compliance Alert (توصية أمنية)

تعدد الأسماء والكيانات آمن فقط إذا كانت جميعها تعمل تحت قبة Mihwar.
يجب التحقق فوراً من أن كل كيان من الكيانات الـ 11+ قد استلم `architecture_directive.md` وتم تسجيله في Mihwar.
أي كيان غير مسجّل يُعامل كخطر ويُعطّل وصوله حتى يتم الامتثال.
