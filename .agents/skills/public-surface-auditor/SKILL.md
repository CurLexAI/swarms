---
name: public-surface-auditor
description: perform safe read-only public web surface audits using curl/header checks. use when checking lexprim.com or any public endpoint for https redirect, tls posture, hsts, csp, cors, security headers, exposed admin/api/health paths, rate-limit headers, and public readiness. do not brute force, fuzz, login, or modify anything.
---

# Public Surface Auditor

## Safe commands

Use read-only checks only:

```powershell
curl.exe -I https://www.lexprim.com
curl.exe -I https://lexprim.com
curl.exe -I https://www.lexprim.com/admin
curl.exe -I https://www.lexprim.com/api
```

## Required headers

* Strict-Transport-Security
* Content-Security-Policy
* X-Frame-Options or `frame-ancestors`
* X-Content-Type-Options
* Referrer-Policy
* Permissions-Policy

## Verdict

* PASS: headers present, protected routes return 401/403, no broad CORS.
* PASS_WITH_MINOR_HARDENING: only minor header hardening remains.
* HOLD: material security control is missing.
* BLOCK: public route exposes sensitive function or secrets.
