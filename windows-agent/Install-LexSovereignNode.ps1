[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)][string]$RegistryPath,
  [string]$StateDirectory = "$env:ProgramData\LexSovereignNode",
  [switch]$Apply,
  [switch]$Rollback,
  [switch]$ConfirmRollback
)
$ErrorActionPreference = 'Stop'
if ($Rollback) {
  if (-not $ConfirmRollback) { throw 'Rollback requires -ConfirmRollback.' }
  if (-not $StateDirectory.StartsWith($env:ProgramData, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'StateDirectory must be under ProgramData.' }
  if (Test-Path -LiteralPath $StateDirectory) { Remove-Item -LiteralPath $StateDirectory -Recurse -Force }
  Write-Output 'Local Lex Sovereign Node state removed. Revoke remote authorization separately.'
  exit 0
}
if (-not $RegistryPath -or -not (Test-Path -LiteralPath $RegistryPath)) { throw 'A valid -RegistryPath is required.' }
$registry = Get-Content -Raw -LiteralPath $RegistryPath | ConvertFrom-Json
if ($registry.role -ne 'lex-sovereign-node' -or $registry.attestation.key_env -eq $registry.heartbeat.key_env) { throw 'Registry contract validation failed.' }
Write-Output "Validated registry for $($registry.node_id)."
Write-Output "Would create protected state directory: $StateDirectory"
if (-not $Apply) { Write-Output 'Dry run complete. Re-run with -Apply after approval.'; exit 0 }
New-Item -ItemType Directory -Path $StateDirectory -Force | Out-Null
Copy-Item -LiteralPath $RegistryPath -Destination (Join-Path $StateDirectory 'registry.json') -Force
$operator = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
icacls $StateDirectory /inheritance:r /grant:r "$operator:(OI)(CI)F" 'Administrators:(OI)(CI)F' 'SYSTEM:(OI)(CI)F' | Out-Null
Write-Output 'Installation complete. Network enrollment and transport remain operator-managed.'
