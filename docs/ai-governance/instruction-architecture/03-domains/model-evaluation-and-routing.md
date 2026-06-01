# Domain: Model Evaluation and Routing

**النطاق:** توجيه النماذج، تصنيف المهام، سياسة اختيار النماذج
**المرجع الأساسي:** `.agents/router/`، `.agents/config/agents.yaml`

---

## محرك توجيه النماذج (Qarar)

```
TaskProfile → task_classifier.py
           → model_policy_engine.py
           → model_router.py
           → ExecutionPlan
```

`ExecutionPlan` يحدد: الوكيل الأساسي، خطوات التحقق، توجيه المراجع.
يُدرج `bayyinah_validation_gate` للمهام عالية/حرجة الخطورة.

---

## سياسة توجيه النماذج

| معيار المهمة | المزود | النموذج | يتطلب مراجع |
|---|---|---|---|
| خطورة حرجة أو دقة قانونية عربية | Anthropic | claude-opus/sonnet | نعم (Bayyinah) |
| multimodal | OpenAI | gpt-current | يعتمد على الخطورة |
| coding / code_review / agent_creation | Modal vLLM | mihwar / bayyinah | نعم (إلا code_review) |
| fast_draft | OpenAI | gpt-current | يعتمد على الخطورة |
| long_context_analysis | Anthropic | claude-sonnet | نعم (Bayyinah) |

---

## نماذج الوكلاء

### Mihwar

```yaml
model: deepseek-ai/DeepSeek-Coder-V2-Instruct
size: 236B (MoE — 21B active)
context_window: 128000
benchmark_humaneval: "90.2"
gpu: A100-80GB × 2
temperature: 0.1  # منخفضة — كود حتمي
```

### Bayyinah

```yaml
model: Qwen/Qwen2.5-Coder-32B-Instruct
size: 32B
context_window: 131072
license: Apache 2.0
benchmark_humaneval: "92.7"
gpu: A100-80GB × 1
temperature: 0.0  # صفر — دقة قصوى للمراجعة
```

---

## أنواع المهام المُصنَّفة

```python
class TaskKind(Enum):
    CODING              # → Mihwar
    CODE_REVIEW         # → Bayyinah
    AGENT_CREATION      # → Mihwar + Bayyinah validation
    FAST_DRAFT          # → OpenAI
    LONG_CONTEXT_ANALYSIS  # → Anthropic
```

---

## استدعاء الوكلاء

```bash
# استدعاء مباشر
python3 .agents/invoke.py mihwar "وصف المهمة"
python3 .agents/invoke.py bayyinah --diff
python3 .agents/invoke.py bayyinah --file src/auth.py

# خط الأنابيب الكامل (Mihwar → Bayyinah)
python3 .agents/invoke.py pipeline "أضف rate limiting للـ API"

# نشر Modal
modal deploy .agents/modal_app.py
```

---

## الأسرار المطلوبة للتشغيل

```
BAYYINAH_ENDPOINT   — SET/UNSET (لا تطبع القيمة)
MIHWAR_ENDPOINT     — SET/UNSET
AGENT_API_TOKEN     — SET/UNSET
MODAL_TOKEN_ID      — SET/UNSET (اختياري)
MODAL_TOKEN_SECRET  — SET/UNSET (اختياري)
```
