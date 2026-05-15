# Windows Tor Browser OPSEC Baseline

Status: OPERATIONAL GUIDANCE
Scope: Windows endpoint baseline for private browsing research with Tor Browser.
Repository fit: operations documentation only; this does not add product code, a public route, a backend service, an always-on agent, or runtime activation.

## Recommendation

Use **Tor Browser on Windows only for medium-risk private browsing and research compartmentalization**. For high-risk identity protection, use Tails or Whonix/Qubes instead of a normal Windows host.

Best Windows path:

1. Install Tor Browser for Windows only from the official Tor Project download page: `https://www.torproject.org/download/`.
2. Verify the Windows download signature before using it when the session is sensitive.
3. Run Tor Browser as a dedicated research profile, not as a daily browser replacement.
4. Set Tor Browser security level to **Safer** by default.
5. Move to **Safest** for hostile websites, unknown documents, or high-risk investigations.
6. Do not install browser extensions.
7. Do not sign in to personal Google, Microsoft, Apple, GitHub, bank, telecom, or social accounts through the same identity compartment.
8. Prefer `.onion` services where available.
9. Keep downloads inside a disposable folder and open documents only after metadata stripping or inside a sandbox/VM.
10. Do not maximize or frequently resize Tor Browser windows; preserve fingerprinting resistance.
11. Run the Windows baseline checker in `scripts/commander/windows-tor-opsec-baseline.ps1` before sensitive sessions.

## Official Windows source

The authoritative Windows download source is the Tor Project download page:

```text
https://www.torproject.org/download/
```

Use the **Download for Windows** option from that page. For sensitive sessions, also use the adjacent **Signature** link to verify the installer before first launch.

Do not use repackaged installers, third-party mirrors, browser-extension bundles, cracked installers, or download sites that add wrappers around the Tor Browser installer.

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

### Security level

Default to **Safer**.

Use **Safest** when:

- visiting unknown links;
- researching hostile infrastructure;
- handling whistleblower or legal-intelligence intake;
- viewing untrusted documents or media;
- conducting investigations where JavaScript is not required.

Avoid **Standard** unless the target site cannot function otherwise and the session is low-risk.

### Extensions and plugins

Do not install extensions. Extensions increase fingerprint uniqueness and can bypass or weaken browser-level privacy assumptions.

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

Do not maximize the Tor Browser window. Avoid resizing during the session. This preserves letterboxing and reduces screen-dimension fingerprinting.

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

### Medium-risk research

- Windows host.
- Tor Browser security level: Safer.
- No extensions.
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

Do not rely on normal Windows + Tor Browser for:

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

> Use Tor Browser for Windows from `https://www.torproject.org/download/`, verify the signature for sensitive sessions, use `Safer` as the default, `Safest` for high-risk sessions, no extensions, no personal accounts, no host document opening, and a dedicated identity compartment. Treat Windows as acceptable for research, not as the final architecture for strong anonymity.
