param(
  [string]$RepoRoot = "",
  [switch]$StrictAzureLogin
)

$ErrorActionPreference = "Continue"
$failures = 0

function Check($name, $scriptBlock) {
  try {
    & $scriptBlock
    Write-Host "[OK] $name" -ForegroundColor Green
  }
  catch {
    $script:failures++
    Write-Host "[FAIL] $name :: $($_.Exception.Message)" -ForegroundColor Red
  }
}

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
  $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
}

Write-Host "Verifying Azure AI workshop environment" -ForegroundColor Cyan
Write-Host "Repo: $RepoRoot"

Check "Git available" {
  $v = git --version
  if (-not $v) { throw "git not responding" }
}

Check "Python >= 3.11" {
  $py = Get-Command python -ErrorAction Stop
  $v = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
  $parts = $v.Split('.')
  if ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 11)) {
    throw "Python 3.11+ required, found $v"
  }
}

Check "Azure CLI available" {
  $v = az version --output json
  if (-not $v) { throw "az not responding" }
}

Check "Azure login" {
  az account show --output none
  if ($LASTEXITCODE -ne 0) {
    if ($StrictAzureLogin) { throw "Not logged in (run az login)" }
    else { throw "Not logged in yet (run az login before labs)" }
  }
}

Check "Lab requirements files exist" {
  $req1 = Join-Path $RepoRoot "labs\lab1-intake-assistant\requirements.txt"
  $req2 = Join-Path $RepoRoot "labs\lab2-rag-policy-bot\requirements.txt"
  if (-not (Test-Path $req1)) { throw "Missing: $req1" }
  if (-not (Test-Path $req2)) { throw "Missing: $req2" }
}

Check "Python packages import test" {
  $venvPy = Join-Path $RepoRoot ".venv\Scripts\python.exe"
  if (Test-Path $venvPy) {
    & $venvPy -c "import fastapi,uvicorn,pydantic,dotenv,openai,azure.search.documents; print('imports ok')"
  } else {
    python -c "import fastapi,uvicorn,pydantic,dotenv,openai,azure.search.documents; print('imports ok')"
  }
}

Check "Port 8000 free (recommended for local app)" {
  $inUse = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
  if ($inUse) { throw "Port 8000 is already in use" }
}

Write-Host ""
if ($failures -eq 0) {
  Write-Host "Environment verification PASSED ✅" -ForegroundColor Green
  exit 0
} else {
  Write-Host "Environment verification has $failures failure(s)." -ForegroundColor Yellow
  exit 1
}
