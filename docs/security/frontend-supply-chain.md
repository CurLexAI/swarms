# Frontend Supply Chain Control (Control Hub)

## Scope
- Page: `public/control/index.html`.
- Runtime libraries audited in this surface:
  - Vue
  - marked
  - DOMPurify
  - Lucide (additional runtime dependency present on page)
- Tailwind runtime: not present on this page at audit time.

## Decision
All runtime JavaScript libraries previously loaded from external CDNs are now self-hosted under `public/control/vendor/` with pinned versions and an integrity manifest.

## Pinned Assets
- `vue.global.prod-3.5.13.js`
- `marked.min-12.0.2.js`
- `purify.min-3.1.6.js`
- `lucide.min-0.468.0.js`

Integrity metadata is generated into:
- `public/control/vendor/integrity.json`

## Enforcement Model
1. Bootstrapping fetches `integrity.json`.
2. Each script is loaded from local origin with `integrity` and `crossorigin="anonymous"`.
3. Production behavior (`window.__DEV_EXTERNAL_CDN_FALLBACK__ = false`) blocks external fallback.
4. Development-only override can set `window.__DEV_EXTERNAL_CDN_FALLBACK__ = true` before loader execution.

## Pipeline Requirement
- Run `node scripts/generate-frontend-integrity.mjs` whenever vendor assets change.
- CI/auditors must reject changes where vendor files changed but `integrity.json` was not regenerated.

## Audit Requirements
- Confirm no external CDN URLs exist in `public/control/index.html` for production path.
- Confirm all vendor entries have pinned file names including explicit versions.
- Confirm `integrity.json` contains SHA-384 entries for all required runtime libraries.
- Confirm dev fallback flag remains disabled by default.

## Rationale
- Reduces third-party runtime tampering risk from CDN-path dependency substitution.
- Creates deterministic frontend dependency set for reproducibility and incident response.
- Preserves limited development escape hatch without allowing silent production egress.
