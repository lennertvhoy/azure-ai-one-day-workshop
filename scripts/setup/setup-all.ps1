param(
  [string]$RepoRoot = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
  $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

Write-Host "Azure AI Workshop setup launcher" -ForegroundColor Cyan
Write-Host "Repo: $RepoRoot"
Write-Host ""
Write-Host "Choose setup path:"
Write-Host "  1) Windows native (recommended default)"
Write-Host "  2) WSL (advanced/optional)"
Write-Host "  3) Verify only (Windows)"
Write-Host "  4) Exit"

$choice = Read-Host "Enter choice (1-4)"

switch ($choice) {
  "1" {
    Write-Host "Running Windows install + verify..." -ForegroundColor Yellow
    powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "windows\install.ps1") -RepoRoot $RepoRoot
    powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "windows\verify.ps1") -RepoRoot $RepoRoot
  }
  "2" {
    Write-Host "Running WSL install + verify..." -ForegroundColor Yellow
    wsl bash -lc "cd '$RepoRoot' && bash scripts/setup/wsl/install_wsl.sh '$RepoRoot' && bash scripts/setup/wsl/verify_wsl.sh '$RepoRoot'"
  }
  "3" {
    Write-Host "Running Windows verify only..." -ForegroundColor Yellow
    powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "windows\verify.ps1") -RepoRoot $RepoRoot
  }
  default {
    Write-Host "Exit."
  }
}
