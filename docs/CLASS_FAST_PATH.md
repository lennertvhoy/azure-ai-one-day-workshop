# Class Fast Path (Instructor + Students)

This is the **only** path to use during live delivery.

## Instructor pre-class (before students start)
Do this once per participant (or per team):
1. Provision infra (IaC preferred): Resource Group, Key Vault, Web App, optional Search, AOAI access/deployment.
2. Confirm each participant has:
   - `$RG`
   - `$KV`
   - `$APP`
   - AOAI endpoint/key/deployment available in Key Vault
3. Verify student can run:
   - `az login`
   - `az account show`

> Keep full infra creation details in `infra/RESOURCE_SETUP.md` (reference only).

---

## Student in-class flow (copy/paste, PowerShell)

### 0) Login + confirm provided variables
```powershell
az login
az account show

# Instructor provides these values:
$RG = "<provided-resource-group>"
$KV = "<provided-key-vault>"
$APP = "<provided-webapp-name>"
$LOCATION = "westeurope"

az group show -n $RG -o table
az webapp show -g $RG -n $APP -o table
```

### 1) Configure Web App app settings from Key Vault
```powershell
az webapp config appsettings set -g $RG -n $APP --settings `
  AZURE_OPENAI_ENDPOINT="@Microsoft.KeyVault(SecretUri=https://$KV.vault.azure.net/secrets/azure-openai-endpoint/)" `
  AZURE_OPENAI_API_KEY="@Microsoft.KeyVault(SecretUri=https://$KV.vault.azure.net/secrets/azure-openai-api-key/)" `
  AZURE_OPENAI_DEPLOYMENT="@Microsoft.KeyVault(SecretUri=https://$KV.vault.azure.net/secrets/azure-openai-deployment/)"
```

### 2) (Optional) Verify locally first, then deploy Lab 1 app
```powershell
# optional local run
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\labs\lab1-intake-assistant\requirements.txt
cd labs\lab1-intake-assistant
python -m uvicorn app.main:app --reload
# open http://127.0.0.1:8000/docs
```

Then deploy:
```powershell
az webapp up -g $RG -n $APP -l $LOCATION --runtime "PYTHON:3.11"
```

### 3) Validate Lab 1
Open:
- `https://<APP>.azurewebsites.net/docs`

Test `POST /intake`.

### 4) Continue to Lab 2
Use `labs/lab2-rag-policy-bot/LAB.md` and follow **CLASS mode** sections only.

---

## Rules to avoid confusion
- If `$RG/$KV/$APP` already exist: **do not recreate them**.
- In PowerShell, use `$VAR = "value"` (not `export`).
- Key Vault secret names use dashes, not underscores.
