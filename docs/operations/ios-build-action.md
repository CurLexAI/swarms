# iOS Build Action (`yukiarrr/ios-build-action@v1.12.0`)

This document captures a canonical CI template for building iOS projects (`.xcodeproj` / `.xcworkspace`) and exporting `.ipa` artifacts for delivery pipelines such as DeployGate and TestFlight.

## Scope

- Build iOS app archives from GitHub Actions.
- Sign archives using p12 + provisioning profile inputs.
- Export `.ipa` using `export-method` and optional `export-options` plist.
- Supports hosted and self-hosted runners (self-hosted requires Xcode installation).

## Required Signing Inputs

You must provide one p12 option:

1. Single p12 file
   - `p12-base64` **or** `p12-path`
2. Split key/certificate
   - `p12-key-base64` **or** `p12-key-path`
   - `p12-cer-base64` **or** `p12-cer-path`

You must also provide provisioning profile input:

- `mobileprovision-base64` **or** `mobileprovision-path`

Additional required inputs:

- `project-path`
- `code-signing-identity`
- `team-id`

## Core Optional Inputs

- `workspace-path` (default: empty)
- `export-method` (`app-store`, `ad-hoc`, `package`, `enterprise`, `development`, `developer-id`; default: `app-store`)
- `configuration` (default: `Release`)
- `scheme`
- `certificate-password`
- `output-path` (default: `output.ipa`)
- `update-targets` (newline-delimited; preferred over deprecated `disable-targets`)
- `export-options` (plist path)
- `cloned-source-packages-path`
- `entitlements-file-path`
- `build-sdk`
- `build-destination`
- `build-path`
- `increment-version-number` (`patch` / `minor` / `major` / explicit value)
- `increment-build-number` (`true` / `testflight` / explicit value)
- `bundle-identifier`
- `app-store-connect-api-key-id`
- `app-store-connect-api-key-issuer-id`
- `app-store-connect-api-key-base64`
- `custom-keychain-name` (default: `ios-build.keychain`)

## Security and Encoding Notes

- Store all secrets in GitHub Actions secrets.
- Do not commit `.p12`, `.mobileprovision`, or raw API keys.
- For base64 input generation, ensure output has no line breaks:

```bash
openssl base64 -in MyAppProvisioning.mobileprovision -A
```

## Example — Single p12

```yaml
- uses: yukiarrr/ios-build-action@v1.12.0
  with:
    project-path: Unity-iPhone.xcodeproj
    p12-base64: ${{ secrets.P12_BASE64 }}
    mobileprovision-base64: ${{ secrets.MOBILEPROVISION_BASE64 }}
    code-signing-identity: ${{ secrets.CODE_SIGNING_IDENTITY }}
    team-id: ${{ secrets.TEAM_ID }}
    workspace-path: Unity-iPhone.xcworkspace # optional
```

## Example — Split key and certificate

```yaml
- uses: yukiarrr/ios-build-action@v1.12.0
  with:
    project-path: Unity-iPhone.xcodeproj
    p12-key-base64: ${{ secrets.P12_KEY_BASE64 }}
    p12-cer-base64: ${{ secrets.P12_CER_BASE64 }}
    mobileprovision-base64: ${{ secrets.MOBILEPROVISION_BASE64 }}
    code-signing-identity: ${{ secrets.CODE_SIGNING_IDENTITY }}
    team-id: ${{ secrets.TEAM_ID }}
    workspace-path: Unity-iPhone.xcworkspace # optional
```

## Example — Multiple provisioning profiles

```yaml
- uses: yukiarrr/ios-build-action@v1.12.0
  with:
    project-path: Unity-iPhone.xcodeproj
    p12-base64: ${{ secrets.P12_BASE64 }}
    mobileprovision-base64: |
      ${{ secrets.MY_MOBILEPROVISION_BASE64 }}
      ${{ secrets.YOUR_MOBILEPROVISION_BASE64 }}
    code-signing-identity: ${{ secrets.CODE_SIGNING_IDENTITY }}
    team-id: ${{ secrets.TEAM_ID }}
    export-options: ios/ExportOptions.plist
```

## Example — Custom keychain

```yaml
- uses: yukiarrr/ios-build-action@v1.12.0
  with:
    custom-keychain-name: my-ios-build.keychain
    project-path: Unity-iPhone.xcodeproj
    p12-key-base64: ${{ secrets.P12_KEY_BASE64 }}
    p12-cer-base64: ${{ secrets.P12_CER_BASE64 }}
    mobileprovision-base64: ${{ secrets.MOBILEPROVISION_BASE64 }}
    code-signing-identity: ${{ secrets.CODE_SIGNING_IDENTITY }}
    team-id: ${{ secrets.TEAM_ID }}
    workspace-path: Unity-iPhone.xcworkspace
```

## Minimal Workflow Job

```yaml
name: ios-build

on:
  workflow_dispatch:

jobs:
  build-ios:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build and export IPA
        uses: yukiarrr/ios-build-action@v1.12.0
        with:
          project-path: YourApp.xcodeproj
          workspace-path: YourApp.xcworkspace
          p12-base64: ${{ secrets.P12_BASE64 }}
          mobileprovision-base64: ${{ secrets.MOBILEPROVISION_BASE64 }}
          code-signing-identity: ${{ secrets.CODE_SIGNING_IDENTITY }}
          team-id: ${{ secrets.TEAM_ID }}
          scheme: YourScheme
          export-method: app-store
          output-path: output.ipa
```
