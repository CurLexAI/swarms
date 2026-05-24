param(
  [string]$RegistryPath = "config/models.registry.json"
)

$ErrorActionPreference = "Stop"

function Get-StatusLine([string]$name, [string]$status, [string]$detail) {
  return "[$status] $name :: $detail"
}

$results = @()

$codexVersion = $null
try {
  $codexVersion = codex --version 2>$null
  $results += Get-StatusLine "codex_cli" "GO" "Detected $codexVersion"
} catch {
  $results += Get-StatusLine "codex_cli" "UNVERIFIED" "Codex CLI not available in PATH"
}

try {
  $null = ollama --version
  $results += Get-StatusLine "ollama_runtime" "GO" "Ollama command is available"
} catch {
  $results += Get-StatusLine "ollama_runtime" "NO-GO" "ollama command not found"
}

try {
  $null = modal profile current 2>$null
  $results += Get-StatusLine "modal_auth" "GO" "Modal profile resolved"
} catch {
  $results += Get-StatusLine "modal_auth" "UNVERIFIED" "Modal auth/profile unavailable"
}

try {
  $null = modal volume list 2>$null
  $results += Get-StatusLine "modal_volume_list" "GO" "Modal volumes listed"
} catch {
  $results += Get-StatusLine "modal_volume_list" "UNVERIFIED" "Could not list modal volumes"
}

if (-not (Test-Path $RegistryPath)) {
  $results += Get-StatusLine "registry_file" "NO-GO" "Missing $RegistryPath"
} else {
  $registry = Get-Content -Raw $RegistryPath | ConvertFrom-Json
  foreach ($model in $registry.models) {
    switch ($model.provider) {
      "ollama" {
        try {
          $list = ollama list | Out-String
          if ($list -match [regex]::Escape($model.model)) {
            $results += Get-StatusLine $model.id "GO" "Ollama model exists"
          } else {
            $results += Get-StatusLine $model.id "NO-GO" "Ollama model missing"
          }
        } catch {
          $results += Get-StatusLine $model.id "UNVERIFIED" "Unable to query ollama model list"
        }
      }
      "modal" {
        try {
          $apps = modal app list | Out-String
          if ($apps -match [regex]::Escape($model.app)) {
            $results += Get-StatusLine $model.id "GO" "Modal app present"
          } else {
            $results += Get-StatusLine $model.id "UNVERIFIED" "Modal app not visible"
          }
        } catch {
          $results += Get-StatusLine $model.id "UNVERIFIED" "Unable to list modal apps"
        }
      }
      "openai-compatible" {
        $baseEnv = [Environment]::GetEnvironmentVariable($model.baseUrlEnv)
        $keyEnv = [Environment]::GetEnvironmentVariable($model.apiKeyEnv)
        if ([string]::IsNullOrWhiteSpace($baseEnv) -or [string]::IsNullOrWhiteSpace($keyEnv)) {
          $results += Get-StatusLine $model.id "UNVERIFIED" "Required env vars are not both set"
        } else {
          $results += Get-StatusLine $model.id "GO" "Required env vars exist"
        }
      }
      default {
        $results += Get-StatusLine $model.id "UNVERIFIED" "Provider validation not implemented"
      }
    }
  }
}

$results | ForEach-Object { Write-Output $_ }
