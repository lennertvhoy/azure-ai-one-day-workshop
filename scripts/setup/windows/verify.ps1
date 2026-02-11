param(
  [string]$RepoRoot = "",
  [switch]$StrictAzureLogin
)

$ErrorActionPreference = "Continue"
$PSNativeCommandUseErrorActionPreference = $false
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

function Ensure-AzOnPath {
  if (Get-Command az -ErrorAction SilentlyContinue) { return }
  $azCmd = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
  if (Test-Path $azCmd) {
    $env:Path = "$([System.IO.Path]::GetDirectoryName($azCmd));$env:Path"
  }
}

function Test-PythonCommand {
  param([Parameter(Mandatory=$true)][string]$Mode)
  try {
    if ($Mode -eq "python") {
      & python -c "import sys; print(sys.version_info.major)" *> $null
    } else {
      & py -3.11 -c "import sys; print(sys.version_info.major)" *> $null
    }
    return ($LASTEXITCODE -eq 0)
  } catch {
    return $false
  }
}

function Get-PythonMode {
  if ((Get-Command python -ErrorAction SilentlyContinue) -and (Test-PythonCommand -Mode "python")) { return "python" }
  if ((Get-Command py -ErrorAction SilentlyContinue) -and (Test-PythonCommand -Mode "py")) { return "py" }
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
  $mode = Get-PythonMode
  if (-not $mode) { throw "Python not found (install Python 3.11+)" }
  $v = (Invoke-Python -Args @("-c","import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')") | Out-String).Trim()
  if ($LASTEXITCODE -ne 0) { throw "Python command failed" }
  $parts = $v.Split('.')
  if ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 11)) {
    throw "Python 3.11+ required, found $v"
  }
}

Check "Azure CLI available" {
  Ensure-AzOnPath
  if (-not (Get-Command az -ErrorAction SilentlyContinue)) { throw "az not found" }
  az version --output none *> $null
  if ($LASTEXITCODE -ne 0) { throw "az command failed" }
}

Check "Azure login" {
  Ensure-AzOnPath
  if (-not (Get-Command az -ErrorAction SilentlyContinue)) { throw "az not found" }
  cmd /c "az account show --output none >nul 2>nul"
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
  $code = "import fastapi,uvicorn,pydantic,dotenv,openai,azure.search.documents; print('imports ok')"
  if (Test-Path $venvPy) {
    & $venvPy -c $code
    if ($LASTEXITCODE -ne 0) { throw "Package imports failed in .venv" }
  } else {
    Invoke-Python -Args @("-c",$code)
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
