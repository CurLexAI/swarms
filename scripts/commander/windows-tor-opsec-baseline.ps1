# Windows Tor Browser OPSEC Baseline Checker
# Read-only checker. Does not install software, edit registry, alter browser settings, or connect to Tor.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Findings = New-Object System.Collections.Generic.List[object]

function Add-Finding {
    param(
        [Parameter(Mandatory = $true)][ValidateSet('PASS','WARN','FAIL','INFO')][string]$Status,
        [Parameter(Mandatory = $true)][string]$Control,
        [Parameter(Mandatory = $true)][string]$Detail,
        [Parameter(Mandatory = $true)][string]$Action
    )

    $Findings.Add([pscustomobject]@{
        Status = $Status
        Control = $Control
        Detail = $Detail
        Action = $Action
    }) | Out-Null
}

function Test-CommandAvailable {
    param([Parameter(Mandatory = $true)][string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Get-KnownTorBrowserPaths {
    $paths = New-Object System.Collections.Generic.List[string]

    $candidateRoots = @(
        $env:LOCALAPPDATA,
        $env:APPDATA,
        $env:ProgramFiles,
        ${env:ProgramFiles(x86)},
        (Join-Path $env:USERPROFILE 'Desktop'),
        (Join-Path $env:USERPROFILE 'Downloads')
    ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

    foreach ($root in $candidateRoots) {
        $candidates = @(
            (Join-Path $root 'Tor Browser\Browser\firefox.exe'),
            (Join-Path $root 'Tor Browser\Start Tor Browser.exe')
        )

        foreach ($candidate in $candidates) {
            if (Test-Path -LiteralPath $candidate) {
                $paths.Add($candidate) | Out-Null
            }
        }
    }

    return $paths | Select-Object -Unique
}

function Test-RegistryValuePresent {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Name
    )

    try {
        $value = Get-ItemProperty -LiteralPath $Path -Name $Name -ErrorAction Stop
        return $null -ne $value.$Name
    }
    catch {
        return $false
    }
}

$os = Get-CimInstance -ClassName Win32_OperatingSystem
Add-Finding -Status 'INFO' -Control 'host.os' -Detail ("Detected {0} build {1}" -f $os.Caption, $os.BuildNumber) -Action 'Use Windows only for medium-risk Tor Browser workflows; move high-risk work to Tails, Whonix, or Qubes.'

$torPaths = Get-KnownTorBrowserPaths
if ($torPaths.Count -gt 0) {
    Add-Finding -Status 'PASS' -Control 'tor.installed.path' -Detail ("Found Tor Browser candidate path(s): {0}" -f ($torPaths -join '; ')) -Action 'Confirm the installer came from the official Tor Project distribution channel before use.'
}
else {
    Add-Finding -Status 'WARN' -Control 'tor.installed.path' -Detail 'Tor Browser was not found in common user or program locations.' -Action 'Install Tor Browser from the official Tor Project distribution channel; do not use repackaged installers.'
}

$torProcesses = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match '^(firefox|tor|lyrebird)$' -and ($_.Path -like '*Tor Browser*') }
if ($torProcesses.Count -gt 0) {
    Add-Finding -Status 'INFO' -Control 'tor.running' -Detail ("Tor-related process candidates are running: {0}" -f (($torProcesses | Select-Object -ExpandProperty ProcessName -Unique) -join ', ')) -Action 'Before changing identities, use New Identity inside Tor Browser rather than only refreshing tabs.'
}
else {
    Add-Finding -Status 'INFO' -Control 'tor.running' -Detail 'No Tor Browser process candidate was detected.' -Action 'Start Tor Browser only when the session identity and download handling plan are ready.'
}

$downloads = Join-Path $env:USERPROFILE 'Downloads'
$torSessionDownloads = Join-Path $downloads 'tor-session'
if (Test-Path -LiteralPath $torSessionDownloads) {
    Add-Finding -Status 'PASS' -Control 'downloads.compartment' -Detail ("Dedicated Tor session download folder exists: {0}" -f $torSessionDownloads) -Action 'Keep untrusted downloads in this folder and clear it after the mission.'
}
else {
    Add-Finding -Status 'WARN' -Control 'downloads.compartment' -Detail ("Dedicated Tor session download folder was not found: {0}" -f $torSessionDownloads) -Action 'Create a dedicated per-session download folder and avoid mixing personal files with anonymous research artifacts.'
}

$oneDriveEnv = $env:OneDrive
if (-not [string]::IsNullOrWhiteSpace($oneDriveEnv) -and (Test-Path -LiteralPath $oneDriveEnv)) {
    Add-Finding -Status 'WARN' -Control 'cloudsync.onedrive' -Detail ("OneDrive path is present: {0}" -f $oneDriveEnv) -Action 'Do not store Tor Browser downloads or mission notes in cloud-synced folders.'
}
else {
    Add-Finding -Status 'PASS' -Control 'cloudsync.onedrive' -Detail 'No active OneDrive environment path was detected.' -Action 'Continue avoiding cloud-synced folders for Tor Browser session artifacts.'
}

$clipboardHistoryEnabled = Test-RegistryValuePresent -Path 'HKCU:\Software\Microsoft\Clipboard' -Name 'EnableClipboardHistory'
if ($clipboardHistoryEnabled) {
    $clipboardValue = (Get-ItemProperty -LiteralPath 'HKCU:\Software\Microsoft\Clipboard' -Name 'EnableClipboardHistory').EnableClipboardHistory
    if ($clipboardValue -eq 1) {
        Add-Finding -Status 'WARN' -Control 'windows.clipboard_history' -Detail 'Windows clipboard history appears enabled for the current user.' -Action 'Disable clipboard history before sensitive sessions to reduce accidental identity and content carryover.'
    }
    else {
        Add-Finding -Status 'PASS' -Control 'windows.clipboard_history' -Detail 'Windows clipboard history appears disabled for the current user.' -Action 'Keep clipboard history disabled for sensitive sessions.'
    }
}
else {
    Add-Finding -Status 'INFO' -Control 'windows.clipboard_history' -Detail 'Clipboard history registry value was not found.' -Action 'Verify manually in Windows Settings before high-risk sessions.'
}

$recentDocs = Join-Path $env:APPDATA 'Microsoft\Windows\Recent'
if (Test-Path -LiteralPath $recentDocs) {
    $recentCount = (Get-ChildItem -LiteralPath $recentDocs -ErrorAction SilentlyContinue | Measure-Object).Count
    if ($recentCount -gt 0) {
        Add-Finding -Status 'WARN' -Control 'windows.recent_files' -Detail ("Windows Recent Items contains {0} item(s)." -f $recentCount) -Action 'Avoid opening sensitive downloads on the host. Clear Recent Items after low-risk sessions and use a VM/sandbox for documents.'
    }
    else {
        Add-Finding -Status 'PASS' -Control 'windows.recent_files' -Detail 'Windows Recent Items folder is empty.' -Action 'Keep sensitive document handling out of the host profile.'
    }
}
else {
    Add-Finding -Status 'INFO' -Control 'windows.recent_files' -Detail 'Windows Recent Items folder was not found.' -Action 'Verify file-history behavior manually if using a managed endpoint.'
}

$officeProcesses = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match '^(WINWORD|EXCEL|POWERPNT|AcroRd32|Acrobat|msedge|chrome)$' }
if ($officeProcesses.Count -gt 0) {
    Add-Finding -Status 'WARN' -Control 'document_handlers.running' -Detail ("Potential document/browser handlers running: {0}" -f (($officeProcesses | Select-Object -ExpandProperty ProcessName -Unique) -join ', ')) -Action 'Close personal browsers and document handlers before sensitive Tor Browser sessions.'
}
else {
    Add-Finding -Status 'PASS' -Control 'document_handlers.running' -Detail 'No common personal browser or Office/PDF handler process was detected.' -Action 'Open untrusted files only in an isolated viewer or disposable VM.'
}

$vpnProcesses = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match '(vpn|wireguard|openvpn|tailscale|zerotier|nord|proton)' }
if ($vpnProcesses.Count -gt 0) {
    Add-Finding -Status 'INFO' -Control 'network.vpn_processes' -Detail ("VPN-related process candidates detected: {0}" -f (($vpnProcesses | Select-Object -ExpandProperty ProcessName -Unique) -join ', ')) -Action 'Do not assume VPN plus Tor improves anonymity. Validate the threat model before stacking network layers.'
}
else {
    Add-Finding -Status 'INFO' -Control 'network.vpn_processes' -Detail 'No obvious VPN process candidate was detected.' -Action 'Use Tor Browser directly unless a documented threat model requires a VPN layer.'
}

if (Test-CommandAvailable -Name 'wsl.exe') {
    $wslStatus = & wsl.exe --status 2>$null
    Add-Finding -Status 'INFO' -Control 'host.wsl' -Detail 'WSL is available on this host.' -Action 'Do not move Tor Browser session artifacts into WSL paths unless that is part of a documented compartment plan.'
}
else {
    Add-Finding -Status 'PASS' -Control 'host.wsl' -Detail 'WSL command was not found.' -Action 'No WSL-specific compartment warning applies.'
}

$failCount = ($Findings | Where-Object { $_.Status -eq 'FAIL' }).Count
$warnCount = ($Findings | Where-Object { $_.Status -eq 'WARN' }).Count
$passCount = ($Findings | Where-Object { $_.Status -eq 'PASS' }).Count
$infoCount = ($Findings | Where-Object { $_.Status -eq 'INFO' }).Count

Write-Output '# Windows Tor Browser OPSEC Baseline Report'
Write-Output ''
Write-Output ("Generated: {0}" -f (Get-Date).ToString('u'))
Write-Output ("Summary: PASS={0} WARN={1} FAIL={2} INFO={3}" -f $passCount, $warnCount, $failCount, $infoCount)
Write-Output ''

foreach ($finding in $Findings) {
    Write-Output ("[{0}] {1}" -f $finding.Status, $finding.Control)
    Write-Output ("  Detail: {0}" -f $finding.Detail)
    Write-Output ("  Action: {0}" -f $finding.Action)
    Write-Output ''
}

if ($failCount -gt 0) {
    exit 2
}

if ($warnCount -gt 0) {
    exit 1
}

exit 0
