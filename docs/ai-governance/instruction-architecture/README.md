# Instruction Architecture — CurLexAI/swarms

بنية التعليمات التشغيلية لطبقة عمليات الوكلاء في CurLexAI.

## الغرض

هذه البنية تحوّل تعليمات الوكلاء من مجرد System Prompt نصي إلى طبقة حوكمة معرفية متعددة المستويات. كل ملف هنا هو مصدر حقيقة لجانب محدد من تشغيل الوكلاء.

## الهيكل

```
00-kernel/       → النواة المعرفية — الهوية والمبادئ الجوهرية
01-policies/     → السياسات الإلزامية — الحدود التي لا تُتجاوز
02-modes/        → أوضاع التشغيل — كيف يعمل الوكيل في سياق معين
03-domains/      → نطاقات المعرفة — التخصصات والمجالات
04-agent-profiles/ → ملفات الوكلاء التشغيلية
05-templates/    → قوالب جاهزة للاستخدام
99-archive/      → أرشيف القرارات السابقة
```

## ترتيب التحميل

```
kernel → policies → mode (based on task) → domain (if applicable) → agent profile
```

## المرجع الأساسي

- `docs/decisions/ADR-0001-swarms-boundary.md` — حدود المستودع (الأسبقية المطلقة)
- `.agents/config/agents.yaml` — ملفات الوكلاء الكاملة
- `.agents/policies/` — السياسات التشغيلية
- `AGENTS.md` — دليل التشغيل
