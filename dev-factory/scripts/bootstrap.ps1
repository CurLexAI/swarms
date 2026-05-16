[CmdletBinding()]
param(
  [ValidateSet('core','apps','db','full')]
  [string]$Profile = 'full'
)

$ErrorActionPreference = 'Stop'

function Write-Step {
  param([string]$Message)
  Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Assert-Admin {
  $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
  $isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
  if (-not $isAdmin) {
    throw 'Run this script in an elevated PowerShell session as Administrator.'
  }
}

function Assert-Winget {
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw 'winget is not installed or not on PATH. Install App Installer from Microsoft Store first.'
  }
}

function Install-WingetPackage {
  param(
    [Parameter(Mandatory = $true)][string]$Id,
    [Parameter(Mandatory = $true)][string]$Name,
    [switch]$Exact
  )

  Write-Host "Installing $Name ($Id)" -ForegroundColor Yellow

  $args = @(
    'install',
    '--id', $Id,
    '--accept-package-agreements',
    '--accept-source-agreements',
    '--silent',
    '--disable-interactivity'
  )

  if ($Exact.IsPresent) {
    $args += '--exact'
  }

  $output = & winget @args 2>&1
  $exitCode = $LASTEXITCODE

  if ($exitCode -ne 0) {
    if (($output -join "`n") -match 'No package found matching input criteria') {
      throw "winget package not found: $Id. Validate the package id on this machine."
    }
    if (($output -join "`n") -match 'No applicable upgrade found' -or ($output -join "`n") -match 'already installed') {
      Write-Host "$Name is already installed." -ForegroundColor DarkGray
      return
    }
    throw "Failed to install $Name ($Id). winget exit code: $exitCode`n$($output -join "`n")"
  }
}

function Enable-WSLAndVirtualization {
  Write-Step 'Enabling WSL and virtualization features'

  $features = @(
    'Microsoft-Windows-Subsystem-Linux',
    'VirtualMachinePlatform'
  )

  foreach ($feature in $features) {
    $state = (Get-WindowsOptionalFeature -Online -FeatureName $feature).State
    if ($state -ne 'Enabled') {
      Enable-WindowsOptionalFeature -Online -FeatureName $feature -NoRestart | Out-Null
      Write-Host "Enabled feature: $feature" -ForegroundColor Green
    } else {
      Write-Host "Feature already enabled: $feature" -ForegroundColor DarkGray
    }
  }
}

function Install-WSL {
  Write-Step 'Installing WSL'
  $wslStatus = & wsl --status 2>&1
  if ($LASTEXITCODE -ne 0) {
    & wsl --install --no-distribution
    Write-Host 'WSL base installed. A reboot may be required.' -ForegroundColor Green
  } else {
    Write-Host 'WSL already configured.' -ForegroundColor DarkGray
  }

  $distros = & wsl --list --quiet 2>$null
  if (-not ($distros -match '^Ubuntu$')) {
    & wsl --install -d Ubuntu
    Write-Host 'Ubuntu distribution installed.' -ForegroundColor Green
  } else {
    Write-Host 'Ubuntu distribution already installed.' -ForegroundColor DarkGray
  }
}

function Install-CorePackages {
  Write-Step 'Installing core development packages'
  $packages = @(
    @{ Id = 'Git.Git'; Name = 'Git'; Exact = $true },
    @{ Id = 'Microsoft.VisualStudioCode'; Name = 'Visual Studio Code'; Exact = $true },
    @{ Id = 'CursorAI,Inc.Cursor'; Name = 'Cursor'; Exact = $true },
    @{ Id = 'Microsoft.WindowsTerminal'; Name = 'Windows Terminal'; Exact = $true },
    @{ Id = 'Microsoft.PowerShell'; Name = 'PowerShell 7'; Exact = $true },
    @{ Id = 'Docker.DockerDesktop'; Name = 'Docker Desktop'; Exact = $true }
  )

  foreach ($package in $packages) {
    Install-WingetPackage -Id $package.Id -Name $package.Name -Exact:([bool]$package.Exact)
  }
}

function Install-AppPackages {
  Write-Step 'Installing productivity and document packages'
  $packages = @(
    @{ Id = 'Microsoft.PowerToys'; Name = 'PowerToys'; Exact = $true },
    @{ Id = 'voidtools.Everything'; Name = 'Everything'; Exact = $true },
    @{ Id = 'ShareX.ShareX'; Name = 'ShareX'; Exact = $true },
    @{ Id = 'Obsidian.Obsidian'; Name = 'Obsidian'; Exact = $true },
    @{ Id = 'Bruno.Bruno'; Name = 'Bruno'; Exact = $true },
    @{ Id = 'DBeaver.DBeaver.Community'; Name = 'DBeaver Community'; Exact = $true },
    @{ Id = 'Figma.Figma'; Name = 'Figma'; Exact = $true },
    @{ Id = 'Microsoft.OutlookForWindows'; Name = 'Outlook for Windows'; Exact = $true },
    @{ Id = 'Drawboard.DrawboardPDF'; Name = 'Drawboard PDF'; Exact = $true },
    @{ Id = 'Inkodo.Inkodo'; Name = 'Inkodo'; Exact = $true },
    @{ Id = 'LiquidText.LiquidText'; Name = 'LiquidText'; Exact = $true }
  )

  foreach ($package in $packages) {
    Install-WingetPackage -Id $package.Id -Name $package.Name -Exact:([bool]$package.Exact)
  }
}

function Install-DatabaseHelpers {
  Write-Step 'Installing database and runtime helpers'
  $packages = @(
    @{ Id = 'OpenJS.NodeJS.LTS'; Name = 'Node.js LTS'; Exact = $true }
  )

  foreach ($package in $packages) {
    Install-WingetPackage -Id $package.Id -Name $package.Name -Exact:([bool]$package.Exact)
  }
}

function Start-DockerDesktopIfNeeded {
  Write-Step 'Ensuring Docker Desktop is running'
  $dockerProcess = Get-Process -Name 'Docker Desktop' -ErrorAction SilentlyContinue
  if (-not $dockerProcess) {
    $dockerExe = Join-Path $Env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
    if (Test-Path $dockerExe) {
      Start-Process -FilePath $dockerExe | Out-Null
      Start-Sleep -Seconds 20
    }
  }

  $maxAttempts = 18
  for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
    & docker info *> $null
    if ($LASTEXITCODE -eq 0) {
      Write-Host 'Docker engine is ready.' -ForegroundColor Green
      return
    }
    Start-Sleep -Seconds 5
  }

  throw 'Docker did not become ready in time. Open Docker Desktop and retry.'
}

function Start-LocalDatabases {
  Write-Step 'Starting local databases and services via Docker Compose'
  Push-Location (Resolve-Path (Join-Path $PSScriptRoot '..\config')).Path
  try {
    & docker compose -f .\docker-compose.yml up -d
    if ($LASTEXITCODE -ne 0) {
      throw 'docker compose up failed.'
    }
  } finally {
    Pop-Location
  }
}

function Main {
  Assert-Admin
  Assert-Winget

  switch ($Profile) {
    'core' {
      Enable-WSLAndVirtualization
      Install-WSL
      Install-CorePackages
      Install-DatabaseHelpers
    }
    'apps' {
      Install-AppPackages
    }
    'db' {
      Install-DatabaseHelpers
      Start-DockerDesktopIfNeeded
      Start-LocalDatabases
    }
    'full' {
      Enable-WSLAndVirtualization
      Install-WSL
      Install-CorePackages
      Install-AppPackages
      Install-DatabaseHelpers
      Start-DockerDesktopIfNeeded
      Start-LocalDatabases
    }
  }

  Write-Host "`nBootstrap complete for profile: $Profile" -ForegroundColor Green
  Write-Host 'Reboot if WSL or virtualization features were enabled during this run.' -ForegroundColor Magenta
}

Main
