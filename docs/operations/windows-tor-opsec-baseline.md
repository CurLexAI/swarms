# Windows Private Browsing OPSEC Baseline

Status: OPERATIONAL GUIDANCE
Scope: Windows endpoint baseline for private browsing research with Tor Browser, Mullvad Browser, and normal-browser tracker blocking.
Repository fit: operations documentation only; this does not add product code, a public route, a backend service, an always-on agent, or runtime activation.

## Recommendation

Use **Mullvad Browser on Windows for daily private browsing and low-to-medium risk research**. Use **Tor Browser on Windows only when Tor-network anonymity is required**. Use **Ghostery only in a normal browser compartment** such as Edge, Firefox, Chrome, Brave, Opera, or Safari when the goal is ad/tracker blocking rather than anonymity.

Move high-risk identity protection to Tails or Whonix/Qubes instead of a normal Windows host.

Best Windows path:

1. Install Mullvad Browser for Windows only from the official Mullvad Browser page: `https://mullvad.net/en/browser`.
2. Install Tor Browser for Windows only from the official Tor Project download page: `https://www.torproject.org/download/`.
3. Install Ghostery only from `https://www.ghostery.com/ghostery-ad-blocker` or the official browser extension store for the target browser.
4. Verify signatures before sensitive use when a signature is available.
5. Use Mullvad Browser with a trustworthy VPN when IP masking is required.
6. Use Tor Browser when the mission requires Tor network routing, `.onion` access, or stronger network anonymity.
7. Use Ghostery only for normal-browser ad, popup, cookie-banner, and tracker blocking; do not treat it as an anonymity control.
8. Set Tor Browser security level to **Safer** by default.
9. Move Tor Browser to **Safest** for hostile websites, unknown documents, or high-risk investigations.
10. Do not install browser extensions in Tor Browser or Mullvad Browser beyond the browser's default bundle.
11. Do not sign in to personal Google, Microsoft, Apple, GitHub, bank, telecom, or social accounts through the same identity compartment.
12. Prefer `.onion` services through Tor Browser where available.
13. Keep downloads inside a disposable folder and open documents only after metadata stripping or inside a sandbox/VM.
14. Do not maximize or frequently resize private browsers; preserve fingerprinting resistance and letterboxing behavior.
15. Run the Windows baseline checker in `scripts/commander/windows-tor-opsec-baseline.ps1` before sensitive sessions.

## Official Windows sources

### Mullvad Browser

The authoritative Mullvad Browser source is:

```text
https://mullvad.net/en/browser
```

Mullvad Browser is developed together with the Tor Project. It is designed to reduce tracking and browser fingerprinting, but it does **not** route traffic through the Tor network. Use it with a trustworthy VPN when the mission requires IP masking.

### Tor Browser

The authoritative Tor Browser source is:

```text
https://www.torproject.org/download/
```

Use the **Download for Windows** option from that page. For sensitive sessions, also use the adjacent **Signature** link to verify the installer before first launch.

### Ghostery Tracker & Ad Blocker

The authoritative Ghostery source is:

```text
https://www.ghostery.com/ghostery-ad-blocker
```

Ghostery is a normal-browser privacy extension for blocking ads, popups, cookies, and trackers. It is available for major browsers including Chrome, Firefox, Safari, Edge, Opera, and Brave.

Do not install Ghostery inside Tor Browser or Mullvad Browser. In this baseline, Ghostery belongs only in a separate normal-browser compartment where the mission is convenience privacy, ad blocking, and tracker transparency.

Do not use repackaged installers, third-party mirrors, browser-extension bundles, cracked installers, or download sites that add wrappers around browser installers.

## Browser selection matrix for Windows

| Use case | Best Windows browser/control | Reason |
| --- | --- | --- |
| Daily private browsing | Mullvad Browser | Better usability while reducing tracking and fingerprinting. |
| Normal-browser ad and tracker blocking | Ghostery in Edge/Firefox/Chrome/Brave/Opera/Safari | Blocks ads, popups, cookie banners, and trackers in ordinary browsing. |
| Research where IP masking matters but Tor is not required | Mullvad Browser + trustworthy VPN | VPN masks IP; Mullvad Browser reduces fingerprinting and tracking. |
| `.onion` services | Tor Browser | Mullvad Browser and Ghostery do not provide Tor network routing. |
| High-risk hostile infrastructure research | Tor Browser at Safest, preferably inside Whonix/Tails/Qubes | Stronger network anonymity and compartmentalization. |
| Source protection or whistleblower intake | Not normal Windows | Use Tails, Whonix/Qubes, or a dedicated isolated machine. |
| Logged-in personal browsing | Normal browser + Ghostery only if needed | Account login defeats anonymity; use only as convenience privacy. |

## Why Windows is not the strongest OPSEC host

Windows is usable for private browsing, but it is not ideal for strong anonymity because the base operating environment commonly includes account sync, telemetry surfaces, indexing, recent-file history, cloud backup integrations, document handlers, endpoint security agents, and application-level identity correlation.

This baseline therefore treats Windows as a **constrained convenience environment**, not as the strongest anonymity architecture.

## Threat model

This baseline is designed to reduce:

- cross-site tracking;
- browser fingerprinting;
- extension-based deanonymization;
- accidental identity mixing;
- metadata leaks from downloaded files;
- direct-clearnet access to sensitive destinations when `.onion` is available;
- operational mistakes caused by using a normal daily browser profile.

This baseline does **not** claim protection against:

- endpoint compromise;
- malware or browser zero-days;
- nation-state traffic correlation;
- account-based deanonymization;
- behavioral stylometry;
- physical surveillance;
- malicious downloaded documents opened on the host.

## Browser configuration

### Mullvad Browser

Use Mullvad Browser when the goal is practical privacy on Windows without the latency and compatibility cost of Tor routing.

Recommended configuration:

- Use with a trustworthy VPN when IP masking matters.
- Keep default fingerprinting protections enabled.
- Do not add extra extensions.
- Do not turn it into a personalized daily browser with synced accounts.
- Keep private mode and cookie-clearing behavior intact.
- Avoid resizing or maximizing if the session depends on fingerprint resistance.

Hard limitation:

> Mullvad Browser is not Tor Browser. Without a VPN, it does not mask the public IP address. With a VPN, the VPN provider becomes part of the trust boundary.

### Tor Browser security level

Default to **Safer**.

Use **Safest** when:

- visiting unknown links;
- researching hostile infrastructure;
- handling whistleblower or legal-intelligence intake;
- viewing untrusted documents or media;
- conducting investigations where JavaScript is not required.

Avoid **Standard** unless the target site cannot function otherwise and the session is low-risk.

### Ghostery in normal browsers

Use Ghostery only when the goal is normal-browser privacy improvement, not anonymity.

Recommended configuration:

- Install only from Ghostery's official page or the official browser extension store.
- Use it in Edge, Firefox, Chrome, Brave, Opera, or Safari.
- Keep ad blocking, anti-tracking, and cookie-banner controls enabled unless a trusted site breaks.
- Use allowlists only for trusted sites with a clear business reason.
- Do not install it inside Tor Browser.
- Do not install it inside Mullvad Browser.
- Do not use it as a replacement for Tor network routing, VPN IP masking, or OS-level compartmentalization.

Hard limitation:

> Ghostery is an extension. Extensions increase browser uniqueness. That is acceptable for a normal browsing compartment, but it is the wrong control for Tor Browser or Mullvad Browser compartments where fingerprint uniformity is the goal.

### Extensions and plugins

Do not install extensions in Tor Browser or Mullvad Browser beyond the browser's default bundle. Extensions increase fingerprint uniqueness and can bypass or weaken browser-level privacy assumptions.

Do not enable legacy plugins or external document handlers inside the browsing workflow.

### Identity separation

Create separate operational identities for separate missions. Do not reuse:

- usernames;
- email addresses;
- recovery email addresses;
- phone numbers;
- writing style;
- avatars;
- profile metadata;
- login times;
- document templates.

Use Tor Browser's **New Identity** when changing identity contexts. Use **New Tor Circuit for this Site** only for route refresh without full identity reset.

### Window behavior

Do not maximize the private browsing window when fingerprinting resistance matters. Avoid resizing during the session. This preserves letterboxing and reduces screen-dimension fingerprinting.

## Windows host hygiene

Before a sensitive session:

1. Sign out of personal browser profiles.
2. Disable clipboard sharing into VMs if using a VM.
3. Close cloud-sync folders that may capture downloads.
4. Use a dedicated download folder for the session.
5. Strip metadata before sharing any file.
6. Avoid opening downloaded files directly on the Windows host.
7. Avoid copying text from personal documents into anonymous identities.
8. Avoid using the same keyboard shortcuts, templates, salutations, and writing patterns across identities.

## Recommended Windows operating mode

### Daily private browsing

- Windows host.
- Mullvad Browser.
- Trustworthy VPN if IP masking matters.
- No additional extensions.
- No sensitive identity claims.

### Normal browsing hardening

- Windows host.
- Edge, Firefox, Chrome, Brave, Opera, or Safari.
- Ghostery for ad, popup, cookie-banner, and tracker blocking.
- Personal accounts allowed only when anonymity is not the goal.
- Do not confuse this with anonymous browsing.

### Medium-risk research

- Windows host.
- Mullvad Browser + trustworthy VPN, or Tor Browser at Safer when Tor routing matters.
- No additional extensions.
- Dedicated download folder.
- Metadata stripping before sharing.
- No personal accounts.

### High-risk research

- Windows host only as the outer machine.
- Run Whonix inside a VM or use Tails from external media.
- Tor Browser security level: Safest.
- No host document opening.
- No persistent personal accounts.
- Mission-specific identity compartment.

### Not recommended on normal Windows

Do not rely on normal Windows + a private browser for:

- source protection;
- whistleblower intake;
- adversarial legal investigations;
- hostile-state research;
- regulated evidence handling where attribution failure is unacceptable.

Use Tails, Whonix, Qubes, or a dedicated isolated machine instead.

## Baseline checker

Run from PowerShell:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/commander/windows-tor-opsec-baseline.ps1
```

The checker is read-only. It does not change registry keys, install software, alter browser preferences, or connect to Tor. It reports host-level findings that should be reviewed before a session.

## Interpretation

- `PASS`: no obvious host-level issue was detected by the local checker.
- `WARN`: review before sensitive browsing.
- `FAIL`: fix before sensitive browsing.
- `INFO`: context only.

The checker is intentionally conservative. A clean report does not prove anonymity or operational safety.

## Hard stop rules

Stop and change environment if any of these are true:

- You need to protect a real-world source.
- You must receive sensitive legal evidence.
- You cannot tolerate identity linkage.
- You need to open unknown documents.
- You are already logged into personal accounts in the same workflow.
- You cannot explain the threat model for the session.

## Decision

For Windows, the best practical answer is:

> Use Mullvad Browser from `https://mullvad.net/en/browser` for daily private browsing and low-to-medium risk research, preferably with a trustworthy VPN when IP masking matters. Use Tor Browser from `https://www.torproject.org/download/` when Tor network routing, `.onion` access, or stronger anonymity is required. Use Ghostery from `https://www.ghostery.com/ghostery-ad-blocker` only in a normal browser compartment for ad, popup, cookie-banner, and tracker blocking. For source protection, whistleblower intake, or high-risk investigations, do not rely on normal Windows; use Tails, Whonix/Qubes, or a dedicated isolated machine.
