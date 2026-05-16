# Agent Profile: Qarar — قرار

**المصدر الكنوني:** `.agents/router/` — محرك التوجيه
**الحالة:** مُنفَّذ كمكون برمجي، لا كوكيل LLM مستقل

---

## الهوية

Qarar (قرار) هو **محرك توجيه النماذج** لمنظومة CurLexAI.
يُصنِّف المهام ويختار النموذج والمزود الأنسب.

لا يتحدث مع المستخدم مباشرة — هو طبقة سياسات برمجية.

---

## البنية

```
.agents/router/
├── task_classifier.py      → يُصنِّف نوع المهمة والمخاطرة
├── model_policy_engine.py  → يختار route بناءً على التصنيف
├── model_router.py         → يُنتج ExecutionPlan
└── types.py                → TaskProfile, ModelRoute, ExecutionPlan
```

---

## منطق التوجيه

```python
# مهمة حرجة أو قانونية عربية → Anthropic + Bayyinah
if profile.risk == "critical" or profile.requires_arabic_legal_precision:
    → provider="anthropic", requires_reviewer=True

# multimodal → OpenAI
if profile.requires_multimodal:
    → provider="openai"

# كود → Modal vLLM (Mihwar/Bayyinah)
if profile.kind in {CODING, CODE_REVIEW, AGENT_CREATION}:
    → provider="modal_vllm"

# مسودة سريعة → OpenAI
if profile.kind == FAST_DRAFT:
    → provider="openai"

# تحليل سياق طويل → Anthropic
if profile.kind == LONG_CONTEXT_ANALYSIS:
    → provider="anthropic"
```

---

## التحقق من أن Qarar يعمل

```bash
python3 -m pytest -q tests/test_router_policy.py
python3 -m py_compile .agents/router/model_policy_engine.py
python3 -m py_compile .agents/router/task_classifier.py
```

---

## ملاحظة

لا يوجد حالياً نموذج LLM مُعيَّن لـ Qarar نفسه — هو خوارزمية توجيه نقية.
إذا احتاجت قرارات التوجيه إلى نموذج LLM مستقبلاً، يُكتب ADR جديد.
