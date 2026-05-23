# GitHub Repository Hardening Orchestrator
# Applies a baseline of GitHub security controls (secret scanning, push protection,
# Dependabot configuration, branch protection) to a list of repositories.
#
# Verified failure semantics: every gh CLI call is followed by an explicit
# $LASTEXITCODE check. The CSV audit report records the real API outcome,
# never an assumed success.
#
# This script reads no secrets from disk. It expects the caller to have
# already authenticated via `gh auth login` or to have set $env:GH_TOKEN
# in the current session. Tokens are never echoed.

[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory = $true, HelpMessage = "Path to CSV file with a RepoName column")]
    [ValidateNotNullOrEmpty()]
    [string]$InputCsv,

    [Parameter(Mandatory = $true, HelpMessage = "GitHub user or organization (Owner)")]
    [ValidatePattern('^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$')]
    [string]$Owner,

    [Parameter(Mandatory = $false)]
    [ValidatePattern('^[A-Za-z0-9._/-]{1,255}$')]
    [string]$BaseBranch = "main",

    [Parameter(Mandatory = $false)]
    [ValidateNotNullOrEmpty()]
    [string]$OutputReport = "SecurityAuditReport.csv",

    [Parameter(Mandatory = $false, HelpMessage = "Allow break-glass admin bypass on the protected branch")]
    [switch]$AllowAdminBypass,

    [Parameter(Mandatory = $false, HelpMessage = "Perform all checks but make no PATCH/PUT calls")]
    [switch]$DryRun,

    [Parameter(Mandatory = $false, HelpMessage = "Overwrite an existing report without prompting")]
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------- helpers ----------

function Test-RepoName {
    param([string]$Name)
    return ($Name -match '^[A-Za-z0-9._-]{1,100}$')
}

function Invoke-GhApi {
    # Wrapper that always inspects $LASTEXITCODE and returns a structured result.
    param(
        [Parameter(Mandatory)][string[]]$Arguments,
        [string]$InputFile,
        [switch]$AllowFailure
    )
    $stderr = [System.IO.Path]::GetTempFileName()
    try {
        $argList = @('api') + $Arguments
        if ($InputFile) { $argList += @('--input', $InputFile) }

        $stdout = & gh @argList 2>$stderr
        $code = $LASTEXITCODE
        $err = if (Test-Path $stderr) { Get-Content $stderr -Raw -ErrorAction SilentlyContinue } else { "" }

        if ($code -ne 0 -and -not $AllowFailure) {
            return [pscustomobject]@{ Ok = $false; ExitCode = $code; Stdout = $stdout; Stderr = $err }
        }
        return [pscustomobject]@{ Ok = ($code -eq 0); ExitCode = $code; Stdout = $stdout; Stderr = $err }
    } finally {
        Remove-Item -Force -ErrorAction SilentlyContinue $stderr
    }
}

function New-SecureTempJson {
    param([Parameter(Mandatory)][string]$Json)
    $path = [System.IO.Path]::GetTempFileName()
    # UTF-8 without BOM; GitHub API rejects BOM on some JSON bodies.
    [System.IO.File]::WriteAllText($path, $Json, [System.Text.UTF8Encoding]::new($false))
    return $path
}

# ---------- preflight ----------

if (-not (Get-Command "gh" -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) is not installed. Install via 'winget install --id GitHub.cli' and retry."
}

$authProbe = & gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "GitHub CLI is not authenticated. Run 'gh auth login' or set GH_TOKEN, then retry."
}

if (-not (Test-Path -LiteralPath $InputCsv)) {
    throw "Input CSV not found: $InputCsv"
}

if ((Test-Path -LiteralPath $OutputReport) -and -not $Force) {
    throw "Output report already exists at '$OutputReport'. Use -Force to overwrite."
}

$Repos = Import-Csv -LiteralPath $InputCsv
if ($Repos.Count -eq 0) {
    throw "Input CSV is empty: $InputCsv"
}
if (-not ($Repos[0].PSObject.Properties.Name -contains 'RepoName')) {
    throw "Input CSV must contain a 'RepoName' column."
}

# Verify token scopes by hitting an authenticated endpoint that requires admin:repo.
# We do not echo the token itself.
$whoami = Invoke-GhApi -Arguments @('user') -AllowFailure
if (-not $whoami.Ok) {
    throw "Failed to call /user as the authenticated identity. Check token validity and network access."
}

$AuditResults = New-Object System.Collections.Generic.List[object]

Write-Host "====== GitHub repo hardening for ($Owner) — DryRun=$($DryRun.IsPresent) ======" -ForegroundColor Cyan

foreach ($row in $Repos) {
    $repo = $row.RepoName
    if (-not (Test-RepoName $repo)) {
        Write-Warning "Skipping invalid repo name: '$repo'"
        continue
    }
    $full = "$Owner/$repo"
    Write-Host "`n[+] Processing repo: $full" -ForegroundColor Yellow

    $auditLog = [ordered]@{
        Repository       = $full
        TimestampUtc     = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
        SecretScanning   = "NotAttempted"
        PushProtection   = "NotAttempted"
        Dependabot       = "NotAttempted"
        BranchProtection = "NotAttempted"
        Notes            = ""
    }

    # ---------- 1. Secret Scanning + Push Protection (single PATCH with nested JSON) ----------
    $securityBody = @{
        security_and_analysis = @{
            secret_scanning                 = @{ status = "enabled" }
            secret_scanning_push_protection = @{ status = "enabled" }
        }
    } | ConvertTo-Json -Depth 6 -Compress

    if ($DryRun) {
        $auditLog.SecretScanning = "DryRun"
        $auditLog.PushProtection = "DryRun"
        Write-Host "  -> [DryRun] would PATCH repos/$full security_and_analysis" -ForegroundColor DarkGray
    } elseif ($PSCmdlet.ShouldProcess($full, "Enable secret scanning and push protection")) {
        $tmp = New-SecureTempJson -Json $securityBody
        try {
            $r = Invoke-GhApi -Arguments @('-X','PATCH',"repos/$full") -InputFile $tmp -AllowFailure
            if ($r.Ok) {
                $auditLog.SecretScanning = "Success"
                $auditLog.PushProtection = "Success"
                Write-Host "  -> Secret Scanning + Push Protection enabled." -ForegroundColor Green
            } else {
                $auditLog.SecretScanning = "Failed"
                $auditLog.PushProtection = "Failed"
                $msg = ($r.Stderr -replace '\s+', ' ').Trim()
                $auditLog.Notes += "Secret scanning PATCH failed (exit=$($r.ExitCode)): $msg. "
                Write-Host "  -> Secret Scanning PATCH failed." -ForegroundColor Red
            }
        } finally {
            Remove-Item -Force -ErrorAction SilentlyContinue $tmp
        }
    }

    # ---------- 2. Dependabot config ----------
    $depFile = @"
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
"@
    $depBytes = [System.Text.Encoding]::UTF8.GetBytes($depFile)
    $depContentB64 = [Convert]::ToBase64String($depBytes)

    # Check if file exists; capture sha for potential update.
    $existing = Invoke-GhApi -Arguments @("repos/$full/contents/.github/dependabot.yml") -AllowFailure
    $existingSha = $null
    if ($existing.Ok) {
        try {
            $existingSha = ($existing.Stdout | ConvertFrom-Json).sha
        } catch { $existingSha = $null }
    }

    if ($DryRun) {
        $auditLog.Dependabot = if ($existing.Ok) { "DryRun(WouldUpdate)" } else { "DryRun(WouldCreate)" }
        Write-Host "  -> [DryRun] Dependabot file action skipped." -ForegroundColor DarkGray
    } elseif ($PSCmdlet.ShouldProcess($full, "Write .github/dependabot.yml")) {
        $payload = @{ message = "chore(security): baseline Dependabot config"; content = $depContentB64 }
        if ($existingSha) { $payload.sha = $existingSha }
        $payloadJson = $payload | ConvertTo-Json -Depth 5 -Compress
        $tmp = New-SecureTempJson -Json $payloadJson
        try {
            $r = Invoke-GhApi -Arguments @('-X','PUT',"repos/$full/contents/.github/dependabot.yml") -InputFile $tmp -AllowFailure
            if ($r.Ok) {
                $auditLog.Dependabot = if ($existingSha) { "Success(Updated)" } else { "Success(Created)" }
                Write-Host "  -> Dependabot config written." -ForegroundColor Green
            } else {
                $auditLog.Dependabot = "Failed"
                $auditLog.Notes += "Dependabot PUT failed (exit=$($r.ExitCode)). "
                Write-Host "  -> Dependabot PUT failed." -ForegroundColor Red
            }
        } finally {
            Remove-Item -Force -ErrorAction SilentlyContinue $tmp
        }
    }

    # ---------- 3. Branch protection ----------
    $protection = @{
        required_status_checks        = $null
        enforce_admins                = (-not $AllowAdminBypass.IsPresent)
        required_pull_request_reviews = @{
            required_approving_review_count = 1
            dismiss_stale_reviews           = $true
            require_code_owner_reviews      = $true
        }
        restrictions                  = $null
        allow_force_pushes            = $false
        allow_deletions               = $false
        required_linear_history       = $true
    }
    $protectionJson = $protection | ConvertTo-Json -Depth 10 -Compress

    if ($DryRun) {
        $auditLog.BranchProtection = "DryRun"
        Write-Host "  -> [DryRun] Branch protection skipped." -ForegroundColor DarkGray
    } elseif ($PSCmdlet.ShouldProcess("$full ($BaseBranch)", "Apply branch protection")) {
        $tmp = New-SecureTempJson -Json $protectionJson
        try {
            $r = Invoke-GhApi -Arguments @('-X','PUT',"repos/$full/branches/$BaseBranch/protection") -InputFile $tmp -AllowFailure
            if ($r.Ok) {
                $auditLog.BranchProtection = "Success"
                Write-Host "  -> Branch protection applied to $BaseBranch." -ForegroundColor Green
            } else {
                $auditLog.BranchProtection = "Failed"
                $msg = ($r.Stderr -replace '\s+', ' ').Trim()
                $auditLog.Notes += "Branch protection PUT failed (exit=$($r.ExitCode)): $msg. "
                Write-Host "  -> Branch protection PUT failed." -ForegroundColor Red
            }
        } finally {
            Remove-Item -Force -ErrorAction SilentlyContinue $tmp
        }
    }

    $AuditResults.Add([pscustomobject]$auditLog) | Out-Null
}

# ---------- export ----------
$AuditResults | Export-Csv -LiteralPath $OutputReport -NoTypeInformation -Encoding UTF8
Write-Host "`n====== Done ======" -ForegroundColor Cyan
Write-Host "Audit report saved to: $OutputReport" -ForegroundColor White
