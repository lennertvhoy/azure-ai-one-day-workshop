param(
  [string]$CourseCode = "azure-ai-1day",
  [switch]$WhatIf
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
  throw "Azure CLI not found."
}

az account show --output none 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Host "No active Azure login. Starting az login..." -ForegroundColor Yellow
  az login | Out-Null
}

$now = (Get-Date).ToUniversalTime()
$rgsJson = az group list --query "[?tags.course=='$CourseCode'].[name,tags.expiresAt]" -o json
$rgs = $rgsJson | ConvertFrom-Json

if (-not $rgs -or $rgs.Count -eq 0) {
  Write-Host "No resource groups found for course '$CourseCode'."
  exit 0
}

foreach ($rg in $rgs) {
  $rgName = $rg[0]
  $expiresAt = $rg[1]

  if ([string]::IsNullOrWhiteSpace($expiresAt)) {
    Write-Host "Skipping $rgName (no expiresAt tag)." -ForegroundColor DarkYellow
    continue
  }

  $expiry = [DateTime]::Parse($expiresAt).ToUniversalTime()
  if ($expiry -le $now) {
    if ($WhatIf) {
      Write-Host "[WhatIf] Would delete expired RG: $rgName (expired $expiresAt)" -ForegroundColor Yellow
    } else {
      Write-Host "Deleting expired RG: $rgName (expired $expiresAt)" -ForegroundColor Yellow
      az group delete --name $rgName --yes --no-wait
    }
  } else {
    Write-Host "Keep $rgName (expires $expiresAt)"
  }
}
