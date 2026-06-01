# Archive: Monolith Reduction Plan

**الحالة:** مؤرشف — القرار اتُّخذ عبر ADR-0001
**التاريخ:** 2026-05-16

---

## الخلفية

في مراحل سابقة، كان هناك اقتراح لجعل `CurLexAI/swarms` monorepo كاملاً يشمل:
- واجهات REST/GraphQL
- صفحات تسويقية
- بنية RAG كاملة
- كود منتج LexPrim/Qarar

---

## القرار المُتخذ (ADR-0001)

تم رفض هذا المسار. المستودع يبقى **طبقة عمليات الوكلاء فقط**.

خط الأنابيب الكامل:
```
User → Codex Commander → Repository → Render → Cloudflare → Modal (sovereign)
```

ليس:
```
User → Public API → Database → Frontend → Marketing Pages → ...
```

---

## الخطوط الحمراء (محظور نهائياً)

```
backend_fastapi/
src/routes/
src/pipeline/
src/factory/
src/control-hub/
src/api/
public/index.html
صفحات تسويقية
خطوط RAG عامة
واجهات REST/GraphQL عامة
autoStart flags
كود منتج LexPrim/Qarar
```

يفرض `adr-0001-boundary-gate.sh` هذه القائمة تلقائياً.

---

## الدرس المستفاد

بدون حد واضح موثق (ADR)، تتكرر المقترحات نفسها في كل جلسة جديدة.
ADR-0001 هو الحاجز الدائم ضد هذا التكرار.

## المرجع

`docs/decisions/ADR-0001-swarms-boundary.md`
