# متطلبات نقل النماذج إلى نماذج محلية (Local Models) في المستودع

بناءً على بنية المستودع الحالية، بعد نقل نماذج الذكاء الاصطناعي (مثل Mihwar و Bayyinah) من بيئة Modal السحابية السيادية إلى نماذج محلية (Local Models) باستخدام Ollama أو vLLM محلي، ستحتاج إلى إجراء التغييرات التالية في المستودع لضمان عمل النظام بشكل صحيح:

### 1. إعدادات الوكلاء (Agent Configuration)
- **ملف `.agents/config/agents.yaml`**: يجب تحديث إعدادات الوكلاء (`mihwar` و `bayyinah`). يجب إزالة قسم `modal:` واستبداله بإعدادات النماذج المحلية (مثل `provider: local_ollama`).
- **تحديث مسارات الاستدلال (`inference`)**: تعديل `engine` ليكون `ollama` أو `llama.cpp` بدلاً من `vllm` المخصص للسحابة، وتحديث `base_url` إذا لزم الأمر.

### 2. سياسات التشغيل (Runtime Policy)
- **ملف `src/policy/runtime-policy.ts`**:
  - إزالة `modal-mihwar` و `modal-bayyinah` من قائمة `currentProviderOrder` والاعتماد بشكل أساسي على `ollama-qwen-local` و `ollama-deepseek-local`.
  - تحديث `providerRegistry` لإزالة سجلات Modal أو تعديل تصنيفاتها إذا لزم الأمر.
- **الاختبارات (`tests/runtime-policy.test.ts`)**: تحديث الاختبارات التي تتحقق من وجود Modal في سياسات التشغيل لتتوافق مع البنية المحلية الجديدة.

### 3. متغيرات البيئة والأمان (Environment Variables & Secrets)
- التخلص من الحاجة إلى `MIHWAR_API_TOKEN` و `BAYYINAH_API_TOKEN` و `MODAL_TOKEN_ID` في بيئات التشغيل (GitHub Actions, Render).
- التأكد من تعيين `OLLAMA_BASE_URL` في بيئة التشغيل للاتصال بالخوادم المحلية (مثل `http://localhost:11434` أو اسم الحاوية في `docker-compose`).

### 4. نصوص التشغيل والنشر (Scripts & Deployment)
- **ملف `.agents/modal_app.py`**: يمكن إيقاف استخدامه أو إزالته بالكامل، حيث أنه مخصص لنشر النماذج على Modal.
- **أداة `mcp.json`**: التأكد من أن `.github/copilot/mcp.json` مهيأ للوضع المحلي (`server_offline.py`) كما هو الحال حالياً كإعداد افتراضي بدون أسرار.
- **إعدادات Docker**: تحديث `docker-compose.yml` (الموجود حالياً لدعم `ollama`) ليكون الطريقة الافتراضية والوحيدة لتشغيل واجهة النماذج.

### 5. التوثيق (Documentation)
- تحديث `CLAUDE.md` و `AGENTS.md` لإزالة الإشارات إلى بيئة Modal كبيئة افتراضية.
- تحديث `docs/operations/model-runtime-evidence.md` ليعكس الأدلة الخاصة بالنماذج المحلية.

---
**ملاحظة أمنية**: باستخدام النماذج المحلية، ستحقق متطلبات سياسة `qala-egress-residency.md` بشكل كامل من خلال منع أي بيانات من الخروج من بيئة التحكم المحلية (`LOCAL_CONTROL_PLANE`).
