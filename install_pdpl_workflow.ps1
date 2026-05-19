$ErrorActionPreference = 'Stop'

$repo = 'CurLexAI/swarms'
$workflowSource = Join-Path $PSScriptRoot 'pdpl-article22-ingestion.yml'
$workflowTarget = '.github/workflows/pdpl-article22-ingestion.yml'

if (-not (Test-Path $workflowSource)) {
  throw "CONFIG_NOT_FOUND: $workflowSource"
}

Write-Host "[INFO] Validating GitHub CLI auth"
gh auth status | Out-Null

Write-Host "[INFO] Copying workflow into repository path"
gh repo clone $repo temp_swarms_repo -- --depth 1
Copy-Item $workflowSource (Join-Path $PSScriptRoot "temp_swarms_repo/$workflowTarget") -Force

Push-Location (Join-Path $PSScriptRoot 'temp_swarms_repo')
try {
  git add $workflowTarget
  if (-not (git diff --cached --quiet)) {
    git commit -m 'ci: add PDPL Article 22 ingestion workflow'
    git push origin main
    Write-Host '[OK] Workflow pushed to main.'
  } else {
    Write-Host '[INFO] No workflow changes detected.'
  }
} finally {
  Pop-Location
}
