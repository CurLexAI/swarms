# Policy: Tool and Connector Policy

**المصدر:** `.agents/policies/network-boundary.md` + `.agents/policies/dependency-build-safety.md`

---

## الشبكة

### الوضع الافتراضي

```
وصول الوكيل للإنترنت: مغلق افتراضياً
```

الوصول مسموح فقط عندما تتطلبه المهمة صراحةً أو كان ضمن مسار تحقق موثق.

### مسموح بدون موافقة إضافية

| الفئة | الشروط |
|---|---|
| عمليات GitHub | فقط لمستودع `CurLexAI/swarms` |
| قراءة سجلات الحزم | فقط لتحقق الـ lockfile |
| نشر Modal | فقط عند تكوين أسرار Modal من قِبل المشغّل |
| GitHub Actions | فقط workflows المستودع وAPI GitHub للتعليقات/الفحوصات |

### محظور

1. إرسال محتوى المستودع إلى AI APIs خارجية أثناء صيانة المستودع
2. تحميل ملفات ثنائية من URLs عشوائية
3. أنماط التثبيت: `curl | bash` أو `wget | sh`
4. callbacks أو webhooks لنطاقات خارجية غير معتمدة
5. URLs ديناميكية تتضمن محتوى المستودع أو مسارات ملفات أو tokens أو مقاطع كود
6. نشر diffs خام خارج بنية المراجعة المعتمدة

---

## التبعيات

### القواعد الصارمة

1. لا تثبّت تبعيات إلا إذا اقتضت ذلك عملية التحقق
2. استخدم أوامر تحترم الـ lockfile: `npm ci`، أو `pnpm install --frozen-lockfile`
3. لا تنفّذ lifecycle scripts من تبعيات غير موثوقة بدون مراجعة
4. لا تحذف ملفات lockfile لإجبار التثبيت
5. لا تُدرج في commit: `node_modules`، `.venv`، ذاكرات تخزين البناء، `dist`، أوزان النماذج
6. إضافة/حذف التبعيات يتطلب مراجعة بشرية قبل الدمج

---

## أدوات الوكلاء المعتمدة

| الأداة | الشرط |
|---|---|
| GitHub MCP tools | فقط لمستودع `CurLexAI/swarms` |
| Modal SDK | backend فقط — لا سطح عام |
| `.agents/invoke.py` | عبر سكريبت الاستدعاء المعتمد فقط |
| `scripts/commander/*.sh` | بوابات المستودع المعتمدة |

---

## تقارير الشبكة

```text
NETWORK_CALLS_MADE: domains or NONE
AUTHORIZED: YES/NO/N/A
UNAUTHORIZED_CALLS: YES/NO
CODE_FINDINGS: findings or NONE
```
