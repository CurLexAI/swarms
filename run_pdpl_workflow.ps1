$ErrorActionPreference = 'Stop'

$repo = 'CurLexAI/swarms'
$workflow = 'pdpl-article22-ingestion.yml'

Write-Host "[INFO] Triggering workflow $workflow on $repo"
gh workflow run $workflow --repo $repo --ref main

Write-Host '[INFO] Watching workflow run output'
gh run watch --repo $repo
