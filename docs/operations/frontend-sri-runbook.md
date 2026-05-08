# Frontend CDN SRI Runbook

## Scope
- Canonical HTML shell currently tracked: `public/trust/index.html`.
- CI gate enforces that any `<script src="https://...">` includes:
  - `integrity="sha384-..."`
  - `crossorigin="anonymous"`

## Update Procedure (when upgrading CDN library)
1. Update CDN version URL inside `scripts/generate-frontend-integrity.mjs` (`cdnAssets`).
2. Run:
   ```bash
   npm run integrity:frontend
   ```
3. If HTML includes that CDN script, copy the generated `integrity` and `crossorigin` values from `public/trust/cdn-integrity.json` into the `<script>` tag.
4. Validate gates:
   ```bash
   npm run check:cdn-sri
   npm run test:cdn-sri
   ```

## Runtime Verification Coverage
- Positive path: test confirms local fallback payload matches generated SHA-384.
- Negative path: test mutates hash and confirms mismatch detection.
