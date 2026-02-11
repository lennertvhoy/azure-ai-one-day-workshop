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

function Get-PythonCommand {
  if (Get-Command python -ErrorAction SilentlyContinue) { return "python" }
  if (Get-Command py -ErrorAction SilentlyContinue) { return "py -3.11" }
  return $null
}

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
  $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
}

Write-Host "Verifying Azure AI workshop environment" -ForegroundColor Cyan
Write-Host "Repo: $RepoRoot"

Check "Git available" {
  $v = git --version
  if ($LASTEXITCODE -ne 0 -or -not $v) { throw "git not responding" }
}

Check "Python >= 3.11" {
  $pythonCmd = Get-PythonCommand
  if (-not $pythonCmd) { throw "Python not found (install Python 3.11+)" }
  $v = Invoke-Expression "$pythonCmd -c \"import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')\""
  if ($LASTEXITCODE -ne 0) { throw "Python command failed" }
  $parts = $v.Trim().Split('.')
  if ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 11)) {
    throw "Python 3.11+ required, found $v"
  }
}

Check "Azure CLI available" {
  if (-not (Get-Command az -ErrorAction SilentlyContinue)) { throw "az not found" }
  az version --output none
  if ($LASTEXITCODE -ne 0) { throw "az command failed" }
}

Check "Azure login" {
  if (-not (Get-Command az -ErrorAction SilentlyContinue)) { throw "az not found" }
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
    if ($LASTEXITCODE -ne 0) { throw "Package imports failed in .venv" }
  } else {
    $pythonCmd = Get-PythonCommand
    if (-not $pythonCmd) { throw "Python not found" }
    Invoke-Expression "$pythonCmd -c \"import fastapi,uvicorn,pydantic,dotenv,openai,azure.search.documents; print('imports ok')\""
    if ($LASTEXITCODE -ne 0) { throw "Package imports failed" }
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
