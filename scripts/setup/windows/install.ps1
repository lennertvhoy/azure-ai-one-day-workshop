param(
  [string]$RepoRoot = "",
  [switch]$SkipAzureLogin,
  [switch]$SkipVenv
)

$ErrorActionPreference = "Stop"

function Write-Section($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }

function Assert-Admin {
  $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent())
    .IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
  if (-not $isAdmin) {
    throw "Please run this script in an elevated PowerShell session (Run as Administrator)."
  }
}

function Install-WithWinget {
  param(
    [Parameter(Mandatory=$true)][string]$Id,
    [Parameter(Mandatory=$true)][string]$Name
  )

  $exists = winget list --id $Id --exact 2>$null
  if ($LASTEXITCODE -eq 0 -and $exists) {
    Write-Ok "$Name already installed"
    return
  }

  Write-Host "Installing $Name ($Id)..."
  winget install --id $Id --exact --silent --accept-source-agreements --accept-package-agreements
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to install $Name via winget ($Id)."
  }
  Write-Ok "$Name installed"
}

Assert-Admin

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
  throw "winget is required. Install/upgrade App Installer from Microsoft Store, then retry."
}

Write-Section "Installing workshop prerequisites"
Install-WithWinget -Id "Git.Git" -Name "Git"
Install-WithWinget -Id "Microsoft.VisualStudioCode" -Name "Visual Studio Code"
Install-WithWinget -Id "Python.Python.3.11" -Name "Python 3.11"
Install-WithWinget -Id "Microsoft.AzureCLI" -Name "Azure CLI"

Write-Section "Refreshing PATH for current session"
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

Write-Section "Locating repository"
if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
  $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
}
if (-not (Test-Path $RepoRoot)) { throw "Repo root not found: $RepoRoot" }
Write-Ok "Repo root: $RepoRoot"

Write-Section "Installing Python dependencies"
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw "python command not found after install. Open a new shell and retry."
}

if (-not $SkipVenv) {
  $venvPath = Join-Path $RepoRoot ".venv"
  if (-not (Test-Path $venvPath)) {
    python -m venv $venvPath
    Write-Ok "Created .venv"
  } else {
    Write-Ok ".venv already exists"
  }

  & "$venvPath\Scripts\python.exe" -m pip install --upgrade pip
  & "$venvPath\Scripts\pip.exe" install -r (Join-Path $RepoRoot "labs\lab1-intake-assistant\requirements.txt")
  & "$venvPath\Scripts\pip.exe" install -r (Join-Path $RepoRoot "labs\lab2-rag-policy-bot\requirements.txt")
  Write-Ok "Installed lab requirements in .venv"
} else {
  python -m pip install --upgrade pip
  python -m pip install -r (Join-Path $RepoRoot "labs\lab1-intake-assistant\requirements.txt")
  python -m pip install -r (Join-Path $RepoRoot "labs\lab2-rag-policy-bot\requirements.txt")
  Write-Ok "Installed lab requirements globally"
}

Write-Section "Installing VS Code extensions"
if (Get-Command code -ErrorAction SilentlyContinue) {
  code --install-extension ms-python.python --force | Out-Null
  code --install-extension ms-python.vscode-pylance --force | Out-Null
  code --install-extension ms-azuretools.vscode-azurecli --force | Out-Null
  Write-Ok "VS Code extensions installed"
} else {
  Write-Warn "code command not found (VS Code may need first launch)."
}

if (-not $SkipAzureLogin) {
  Write-Section "Azure login"
  az account show 1>$null 2>$null
  if ($LASTEXITCODE -ne 0) {
    Write-Host "No active Azure session. Running: az login"
    az login
  }
  az account show --output table
}

Write-Section "Done"
Write-Host "Run verification next:" -ForegroundColor Cyan
Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\setup\windows\verify.ps1" -ForegroundColor White
