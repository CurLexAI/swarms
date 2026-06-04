# Policy: Sovereignty and Compliance

**المصدر:** `docs/decisions/ADR-0001-swarms-boundary.md` + `.agents/policies/`
**الإلزامية:** مطلقة — لا تتنازل ولا تُختصر

---

## حدود المستودع (ADR-0001)

`CurLexAI/swarms` هو **طبقة عمليات الوكلاء والتحقق والبيانات السيادية** لبرنامج CurLexAI.

### المحتوى المسموح (خمس فئات فقط)

1. عمليات الوكلاء: catalog، config، providers، router، validators تحت `.agents/`
2. Modal runtime glue: `.agents/modal_app.py` والمحوّلات في `src/services/`
3. بوابات التحقق: `tests/`، `scripts/commander/`، `.agents/validators/`
4. المهارات والسياسات وملفات التشغيل: `.agents/skills/`، `.agents/policies/`، `docs/`
5. خطوط البيانات السيادية: الاستيعاب والتضمين والبحث المتجه ضمن الطبقة السيادية لـ Modal

### الإضافات المحظورة (boundary drift)

```
backend_fastapi/
src/routes/
src/pipeline/
src/factory/
src/control-hub/
src/api/
public/index.html
صفحات تسويقية تحت public/
خطوط RAG
واجهات REST/GraphQL عامة
علامات autoStart على الوكلاء
كود منتج LexPrim/Qarar
```

يفرض `adr-0001-boundary-gate.sh` هذه القائمة تلقائياً.

---

## قاعدة Modal السيادية

**Modal هي backend فقط.**

```
modal.run URLs  →  backend only
Modal SDK imports  →  backend only
Modal tokens  →  secrets manager only
```

يمنع `modal-boundary-gate.sh` تسرب `*.modal.run` أو استيرادات Modal SDK إلى أي سطح عام أو عميل.

---

## الامتثال التنظيمي

لا تدّعي امتثال SAMA أو PDPL أو NCA أو أي تنظيم آخر بدون دليل مستشهد.

---

## سياسة الأسرار

| الفئة | الحكم |
|---|---|
| ملفات `.env` | ممنوع commit |
| مفاتيح API حقيقية | ممنوع في أي مكان |
| `*.modal.run` endpoints | backend فقط |
| رموز GitHub | ممنوع في الكود |
| JWT / OAuth tokens | ممنوع في السجلات |

الأسرار المطلوبة للتشغيل (SET/UNSET فقط — لا تطبع القيم):
`BAYYINAH_ENDPOINT`, `MIHWAR_ENDPOINT`, `BAYYINAH_API_TOKEN`, `MIHWAR_API_TOKEN`

الاختيارية: `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET`, `RENDER_API_TOKEN`, `CLOUDFLARE_API_TOKEN`, `SOVEREIGN_API_KEY`
