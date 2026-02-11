param(
  [Parameter(Mandatory = $true)][string]$StudentCode,
  [string]$CourseCode = "aiws",
  [string]$Location = "westeurope",
  [switch]$WriteFile
)

$ErrorActionPreference = "Stop"

$safe = ($StudentCode.ToLower() -replace '[^a-z0-9-]', '-')
$suffix = (Get-Random)

$vars = [ordered]@{
  LOCATION = $Location
  STUDENT = $safe
  RG = "rg-$CourseCode-$safe-$suffix"
  KV = "kv-$CourseCode-$safe-$suffix"
  PLAN = "plan-$CourseCode-$safe-$suffix"
  APP = "app-$CourseCode-$safe-$suffix"
  AOAI = "aoai-$CourseCode-$safe-$suffix"
  AOAI_DEPLOYMENT = "gpt4omini"
  SEARCH = "srch-$CourseCode-$safe-$suffix"
}

Write-Host "Generated student variables" -ForegroundColor Cyan
$vars.GetEnumerator() | ForEach-Object { Write-Host ("{0}={1}" -f $_.Key, $_.Value) }

Write-Host "`nCopy/paste into PowerShell:" -ForegroundColor Yellow
$vars.GetEnumerator() | ForEach-Object { Write-Host ("`${0} = \"{1}\"" -f $_.Key, $_.Value) }

Write-Host "`nEquivalent Bash exports (optional):" -ForegroundColor Yellow
$vars.GetEnumerator() | ForEach-Object { Write-Host ("export {0}=\"{1}\"" -f $_.Key, $_.Value) }

if ($WriteFile) {
  $path = ".student-vars.$safe.ps1"
  $content = ($vars.GetEnumerator() | ForEach-Object { '$' + $_.Key + ' = "' + $_.Value + '"' }) -join "`n"
  Set-Content -Path $path -Value $content -Encoding UTF8
  Write-Host "`nWrote $path" -ForegroundColor Green
}
