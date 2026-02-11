# IaC Starter — Participant Lab Environments

This folder provides a cost-controlled Azure IaC starter for workshop delivery.

## What it deploys per participant
- 1 Resource Group (tagged with course/owner/expiry)
- 1 Linux App Service Plan (B1)
- 1 Python 3.11 Web App with system-assigned managed identity
- 1 Key Vault (RBAC mode enabled)
- (Optional) 1 Azure AI Search service (Basic)
- RBAC assignment: Web App identity → `Key Vault Secrets User`

## Why this model
- Easy per-participant isolation
- Predictable costs (small SKUs + easy cleanup)
- Scales to paid training operations

## Quick start

```powershell
# login once
az login

# OPTIONAL: generate unique per-student variable values
powershell -ExecutionPolicy Bypass -File .\infra\iac\student-vars.ps1 -StudentCode p01 -WriteFile

# deploy participant p01 (default expiry = now + 8h)
powershell -ExecutionPolicy Bypass -File .\infra\iac\deploy.ps1 -ParticipantId p01 -Owner lenny

# deploy without search (cheaper if only Lab 1)
powershell -ExecutionPolicy Bypass -File .\infra\iac\deploy.ps1 -ParticipantId p02 -NoSearch
```

## Cleanup expired environments

```powershell
# dry run
powershell -ExecutionPolicy Bypass -File .\infra\iac\cleanup-expired.ps1 -WhatIf

# delete expired RGs for this course
powershell -ExecutionPolicy Bypass -File .\infra\iac\cleanup-expired.ps1
```

## Notes
- Default region is `westeurope`.
- Tags include `expiresAt`; cleanup script uses that tag.
- Keep AOAI provisioning separate if your tenant has restricted model approvals.
