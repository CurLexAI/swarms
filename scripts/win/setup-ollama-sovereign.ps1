#Requires -Version 5.1
[CmdletBinding()]
param(
  [string]$BindHost = "127.0.0.1",
  [string]$Origins  = "http://localhost,http://127.0.0.1",
  [int]$Port = 11434,
  [string]$AllowSubnet = "192.168.0.0/16"
)
$ErrorActionPreference = "Stop"
if ($BindHost -eq "0.0.0.0" -or $Origins -eq "*") { Write-Warning "CRITICAL: 0.0.0.0/* exposes models to whole network. Restrict before prod." }
Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force; Start-Sleep 2
[Environment]::SetEnvironmentVariable("OLLAMA_HOST", $BindHost, "User")
[Environment]::SetEnvironmentVariable("OLLAMA_ORIGINS", $Origins, "User")
if ($BindHost -ne "127.0.0.1") { New-NetFirewallRule -DisplayName "Ollama-LAN-$Port" -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port -RemoteAddress $AllowSubnet -ErrorAction SilentlyContinue }
Start-Process "ollama" -ArgumentList "app"; Start-Sleep 4
curl.exe -s "http://$($BindHost):$Port/api/tags" | Out-Null
if ($LASTEXITCODE -eq 0) { Write-Host "OK Ollama @ ${BindHost}:${Port} ORIGINS=$Origins" } else { Write-Error "Not reachable; check Listening line" }
