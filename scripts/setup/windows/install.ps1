param(
  [string]$RepoRoot = "",
  [switch]$SkipAzureLogin,
  [switch]$SkipVenv
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

function Write-Section($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }

function Assert-Admin {
  $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
  $isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
  if (-not $isAdmin) {
    throw "Please run this script in an elevated PowerShell session (Run as Administrator)."
  }
}

function Install-WithWinget {
  param(
    [Parameter(Mandatory=$true)][string]$Id,
    [Parameter(Mandatory=$true)][string]$Name
  )

  $exists = winget list --id $Id --exact --source winget 2>$null
  if ($LASTEXITCODE -eq 0 -and $exists) {
    Write-Ok "$Name already installed"
    return
  }

  Write-Host "Installing $Name ($Id)..."
  winget install --id $Id --exact --source winget --silent --accept-source-agreements --accept-package-agreements
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to install $Name via winget ($Id). Try: winget source reset --force"
  }
  Write-Ok "$Name installed"
}

function Ensure-AzOnPath {
  if (Get-Command az -ErrorAction SilentlyContinue) { return }
  $azCmd = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
  if (Test-Path $azCmd) {
    $env:Path = "$([System.IO.Path]::GetDirectoryName($azCmd));$env:Path"
  }
}

function Get-PythonMode {
  if (Get-Command python -ErrorAction SilentlyContinue) { return "python" }
  if (Get-Command py -ErrorAction SilentlyContinue) { return "py" }
  return $null
}

function Invoke-Python {
  param(
    [Parameter(Mandatory=$true)][string[]]$Args
  )
  $mode = Get-PythonMode
  if ($mode -eq "python") { & python @Args; return }
  if ($mode -eq "py") { & py -3.11 @Args; return }
  throw "Python 3.11+ not found"
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
$pythonMode = Get-PythonMode
if (-not $pythonMode) {
  throw "Python command not found after install. Open a new PowerShell window and retry."
}

if (-not $SkipVenv) {
  $venvPath = Join-Path $RepoRoot ".venv"
  if (-not (Test-Path $venvPath)) {
    Invoke-Python -Args @("-m","venv",$venvPath)
    Write-Ok "Created .venv"
  } else {
    Write-Ok ".venv already exists"
  }

  & "$venvPath\Scripts\python.exe" -m pip install --upgrade pip
  & "$venvPath\Scripts\pip.exe" install -r (Join-Path $RepoRoot "labs\lab1-intake-assistant\requirements.txt")
  & "$venvPath\Scripts\pip.exe" install -r (Join-Path $RepoRoot "labs\lab2-rag-policy-bot\requirements.txt")
  Write-Ok "Installed lab requirements in .venv"
} else {
  Invoke-Python -Args @("-m","pip","install","--upgrade","pip")
  Invoke-Python -Args @("-m","pip","install","-r",(Join-Path $RepoRoot "labs\lab1-intake-assistant\requirements.txt"))
  Invoke-Python -Args @("-m","pip","install","-r",(Join-Path $RepoRoot "labs\lab2-rag-policy-bot\requirements.txt"))
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
  Ensure-AzOnPath
  if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Warn "az command not available in this shell yet. Open a new shell, run az login, then verify script."
  } else {
    az account show --output none *> $null
    if ($LASTEXITCODE -ne 0) {
      Write-Host "No active Azure session. Running: az login"
      az login
    }
    az account show --output table
  }
}

Write-Section "Done"
Write-Host "Run verification next:" -ForegroundColor Cyan
Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\setup\windows\verify.ps1" -ForegroundColor White
