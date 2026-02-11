param(
  [Parameter(Mandatory = $true)][string]$ParticipantId,
  [string]$Location = "westeurope",
  [string]$CourseCode = "azure-ai-1day",
  [string]$Owner = "trainer",
  [string]$ExpiresAt = "",
  [switch]$NoSearch
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
  throw "Azure CLI not found. Install Azure CLI first."
}

az account show --output none 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Host "No active Azure login. Starting az login..." -ForegroundColor Yellow
  az login | Out-Null
}

if ([string]::IsNullOrWhiteSpace($ExpiresAt)) {
  $ExpiresAt = (Get-Date).ToUniversalTime().AddHours(8).ToString("yyyy-MM-ddTHH:mm:ssZ")
}

$deploySearch = if ($NoSearch) { "false" } else { "true" }

Write-Host "Deploying participant environment..." -ForegroundColor Cyan
az deployment sub create \
  --name "iac-$CourseCode-$ParticipantId-$(Get-Date -Format yyyyMMddHHmmss)" \
  --location $Location \
  --template-file "./infra/iac/main.bicep" \
  --parameters participantId="$ParticipantId" location="$Location" courseCode="$CourseCode" owner="$Owner" expiresAt="$ExpiresAt" deploySearch=$deploySearch

if ($LASTEXITCODE -ne 0) {
  throw "Deployment failed"
}

Write-Host "Deployment complete ✅" -ForegroundColor Green
Write-Host "Tip: capture outputs with: az deployment sub list --query \"[0].properties.outputs\""
