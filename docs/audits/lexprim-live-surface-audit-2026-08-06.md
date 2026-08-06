# LexPrim Live Surface Audit — 2026-08-06

> **CONFIDENTIAL — INTERNAL OPERATIONS AUDIT**
> Independent verification of the deployed https://www.lexprim.com surface,
> conducted after an external (GPT) review reached a HOLD verdict. This
> document records what was actually verified against the live site, where
> the external review was right, and where it was materially wrong.
> Evidence labels follow the repository contract
> (`VERIFIED | INFERRED | UNVERIFIED`).

## 1. Deployment fingerprint

- `VERIFIED` — Origin is **Render** (`x-render-origin-server: Render`,
  `rndr-id` header, DNS → 216.24.57.0/24) behind **Cloudflare**
  (`server: cloudflare`).
- `VERIFIED` — Server stack is **Node/Express with Helmet** (header set:
  `x-dns-prefetch-control`, `x-download-options`,
  `x-permitted-cross-domain-policies`).
- `VERIFIED` — Landing page static file `last-modified: 2026-04-27`.
- `VERIFIED` — Frontend `/chat/` is a **Vue 3 CDN app** (`app.js` ~54KB,
  `js/api.js` client), not the React `qarar-platform.jsx` artifact the
  external review analyzed.
- `BLOCKED` — The **source repository feeding the Render service is not
  any accessible CurLexAI repo**. Checked: `swarms` (operations only, per
  ADR-0001), `FRONT` and `website-` (both are stale mirrors of the swarms
  operations tree — neither contains the product frontend). The deploy
  repo must be read off the Render dashboard (Service → Settings →
  Repository) by an operator.

## 2. Central correction to the external review

The external review claimed the deployed chat is a **mock** («تتم إضافة
كائن ثابت SAMPLE... لا يظهر استدعاء fetch»). That is **false for the
deployed application**:

- `VERIFIED` — `chat/js/api.js` implements a real API client
  (`/api/chat`, `/api/chat/direct`, `/api/agents`, `/api/status`,
  `/api/chat/key-status`) with timeout, retry, and typed errors.
- `VERIFIED` — `chat/app.js` (line ~1169) awaits
  `apiClient.sendDirectChat(...)` / `sendAgentChat(...)`; on failure it
  surfaces an error toast — it does **not** fabricate an answer. The
  «بحث عميق» animation is cosmetic while awaiting the real response.
- `VERIFIED` — An anonymous `POST /api/chat/direct` returned **HTTP 200**
  with a live generated PDPL answer, `trace_id`, `confidence: 0.85`,
  `model: "direct"`, `sovereignty: "KSA"`.

The artifact the external review dissected (`qarar-platform.jsx`, object
`SAMPLE`, confidence 0.91) does not match the deployed app (Vue,
default 0.85). Its file-level findings describe **some other copy** of
the frontend — which itself confirms the multiple-divergent-sources
problem, now spanning at least: the deployed Render app, the reviewed
JSX, the empty Grapes Studio project, and the stale `FRONT`/`website-`
mirrors.

## 3. Critical finding: sovereignty misrepresentation in production

This is more serious than anything in the external review, and it is
evidence-backed:

- `VERIFIED` — The landing page publicly claims: «بياناتك لا تخرج من
  المملكة», «امتثال كامل لنظام حماية البيانات», «جميع النماذج تعمل على
  خوادم سيادية — مدعوم بـ Modal.com», and lists DeepSeek R1 32B /
  Qwen 72B "Arabic" / Qwen3 Router / ALLaM 7B as the serving models.
- `VERIFIED` — `GET /api/chat/key-status` (anonymous, HTTP 200) reports
  the backend's **actual configured providers**: OpenAI ("GPT-4 Ready"),
  Anthropic ("Claude Ready"), Perplexity, Groq — all ready; Gemini
  offline. These are external, non-KSA inference APIs.
- `VERIFIED` — The site CSP allows browser `connect-src` to
  `https://*.modal.run`, `https://api.openai.com`,
  `https://api.anthropic.com`, `https://api.perplexity.ai`,
  `https://api.groq.com` — exposing Modal endpoints toward the client
  surface contradicts the Modal-is-backend-only rule, and the external
  AI hosts corroborate the provider list above.
- `INFERRED` — Anonymous chat traffic (user prompts) is served by those
  external providers, while every response is stamped
  `"sovereignty": "KSA"`. The advertised sovereign models are not what
  answers `/api/chat/direct`.

Consequences (operations view; legal review required):

1. The public "data never leaves the Kingdom" claim is **contradicted by
   the platform's own status endpoint**. Under PDPL cross-border rules
   this is a material exposure, not a wording issue.
2. `/api/chat/key-status` leaks provider posture to anonymous callers —
   it should be authenticated or removed.
3. `/api/status` and `/api/agents` return 401 while the chat itself is
   anonymous-open — the auth posture is inverted (telemetry locked,
   inference open, no visible rate limiting).

## 4. Where the external review was right (verified)

- `VERIFIED` — Payments row (تابي/تمارا/Visa/Apple Pay/مدى/STC Pay) is
  live on the landing page despite the "open public sandbox" phase.
- `VERIFIED` — "Qwen 72B Arabic" and "Qwen3 Router" are shown; the
  underlying `Qwen2.5-72B-Instruct-AWQ` is a general multilingual model,
  and no runtime evidence ties any listed model to actual serving.
- `VERIFIED` — A static legal example citing SAMA CSF v2.0 / TLS 1.2 /
  AES-256 is published without an official source link.
- `VERIFIED` — Defensive-wording recommendation is sound and matches
  this repository's own prohibition #3 (no compliance claims without
  cited evidence).
- `UNVERIFIED` — Mobile-viewport defects (dvh/safe-area/composer): the
  prescriptions are generic-plausible but were written against the
  non-deployed JSX artifact; they must be re-validated against the Vue
  app before implementation.

## 5. Required actions (ordered)

1. **Identify the canonical deploy repo** from the Render dashboard and
   bring it under CurLexAI governance (or grant this tooling access).
   Until then every fix prescription has no landing place. `BLOCKED` on
   operator action.
2. **Stop the sovereignty misstatement** (fastest path, no code):
   remove or soften «بياناتك لا تخرج من المملكة» and the sovereign-models
   claim on the landing page until inference actually runs on approved
   sovereign runtimes — or gate `/api/chat/direct` off the external
   providers.
3. **Lock `/api/chat/key-status`** behind auth; review the CSP to remove
   `*.modal.run` and external AI hosts from browser `connect-src`.
4. Add rate limiting + abuse controls + a sensitive-data disclaimer to
   the anonymous chat (it is live and open today).
5. Hide payments behind a feature flag for the sandbox phase.
6. Then (and only then) the responsive/mobile PR, written against the
   real Vue app in the canonical repo — **not** against
   `qarar-platform.jsx`, and **not** inside `swarms` (ADR-0001).

## 6. Verdict on the external review

- Its HOLD decision: **correct**.
- Its site-content findings (claims, payments, model naming, static
  example): **correct and now independently verified**.
- Its central technical claim (chat is a mock with no API path):
  **wrong for the deployed product** — the chat is real, anonymous-open,
  and served by external non-sovereign providers, which is the opposite
  failure and a worse one.
- Its single prescribed action (PR in the "LexPrim/Qarar app repo"):
  **not executable** — no such repo is visible in the CurLexAI org; the
  deploy source must first be identified from Render.

## Verification log (all 2026-08-06, from this session)

```
curl -sI https://www.lexprim.com/            # Render+Cloudflare+Helmet headers, CSP
curl -s  https://www.lexprim.com/chat/app.js # real apiClient send path (line ~1169)
curl -s  https://www.lexprim.com/chat/js/api.js
POST /api/chat/direct                        # 200, live generated answer
GET  /api/chat/key-status                    # 200, external providers ready
GET  /api/status, /api/agents               # 401
git clone (shallow) CurLexAI/FRONT, CurLexAI/website-  # both = stale swarms mirrors
```

No secrets were retrieved or printed; provider states are boolean flags
returned to any anonymous caller.
