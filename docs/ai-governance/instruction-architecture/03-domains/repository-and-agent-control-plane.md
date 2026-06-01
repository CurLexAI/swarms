# Domain: Repository and Agent Control Plane

**النطاق:** عمليات الوكلاء، المستودع، بوابات التحقق، دورات PR
**المرجع الأساسي:** `AGENTS.md`، `.agents/config/agents.yaml`، `scripts/commander/`

---

## الطبولوجيا الكنونية

```
User / iPhone / GitHub / Copilot
  → Codex Commander
  → Repository worktree
  → Render origin
  → Cloudflare edge
  → Modal sovereign model runtime (Bayyinah / Mihwar via vLLM)
  → Bayyinah validation gate
```

---

## الوكلاء الثلاثة

| الوكيل | النموذج | الدور | الطبقة |
|---|---|---|---|
| Mihwar (المحور) | DeepSeek-Coder-V2-Instruct (236B) | مهندس/مُنشئ | 1 |
| Bayyinah (البيّنة) | Qwen2.5-Coder-32B-Instruct | مراجع/محقق | 2 |
| Copilot SWE | GitHub Copilot | مُنفِّذ scaffold فقط | 3 |

---

## المسار الافتراضي

```
Mihwar يُنشئ → Bayyinah تراجع → حتى 3 دورات → موافقة بشرية
```

Bayyinah لا توافق أبداً بنتائج CRITICAL/HIGH غير محلولة.

---

## بوابات التحقق (الترتيب الإلزامي)

```bash
bash scripts/commander/p0-security-test-gate.sh .
bash scripts/commander/modal-boundary-gate.sh .
bash scripts/commander/adr-0001-boundary-gate.sh .
bash scripts/commander/agent-presence-gate.sh .
bash .agents/skills/codex-commander/scripts/codex_commander_gate.sh .
```

---

## المكونات الرئيسية

| المكون | المسار | الدور |
|---|---|---|
| Agent config | `.agents/config/agents.yaml` | مصدر الحقيقة الوحيد للوكلاء |
| Modal runtime | `.agents/modal_app.py` | نقاط نهاية vLLM |
| CLI الاستدعاء | `.agents/invoke.py` | استدعاء الوكلاء |
| مراجعة PR | `.agents/pr_review.py` | Bayyinah review لـ main |
| Router | `.agents/router/` | تصنيف المهام وتوجيه النماذج |
| Validation gate | `.agents/validators/bayyinah_validation_gate.py` | بوابة P0 |
| Node adapter | `src/services/unifiedAgentAdapter.ts` | طبقة Node للوكلاء |
| Security | `src/security/sovereignCyberRadar.ts` | فحص أمني |

---

## أوامر التشغيل

```bash
# Python: تحقق من assets الوكلاء
python3 .agents/validate.py
python3 .agents/invoke.py info

# اختبارات
python3 -m pytest -q tests/
npm test

# TypeScript
npx tsc --noEmit

# Aggregate gate
npm run check
```

---

## نقطة معرفة: TS Blocker موثق

`npx tsc --noEmit` يفشل حالياً بـ:
```
TS2307: Cannot find module '../runners/agentRunner.js'
```
هذا موثق ومتتبع بشكل منفصل. لا تُنشئ حلولاً تخفيه.
