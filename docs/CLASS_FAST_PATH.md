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

Decision for live class:
- Default = **cloud-first functional path** (fastest, least confusion).
- Local run is only a smoke test unless instructor explicitly enables full local mode.

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

⏱️ **Wait 30–60 seconds before the next command block** (let SCM/config settle).

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

⏱️ **Wait until deploy completes**. Do **not** run restart/config commands during deploy.

### 3) Validate Lab 1 (proof it works)
Open:
- `https://<APP>.azurewebsites.net/health` (must return `{"ok":true}`)
- `https://<APP>.azurewebsites.net/docs`

In `/docs`, test `POST /intake` with this payload:
```json
{
  "text": "Invoice INV-001 from Contoso Office Supplies for EUR 1,250.00 due in 14 days."
}
```

Expected: structured JSON including `doc_type`, `entities`, `summary`, `routing`.

If `/health` and `/docs` work but `POST /intake` returns 500:
1. Confirm AOAI deployment exists (example: `gpt4omini`).
2. Confirm Key Vault secrets are set and mapped:
   - `azure-openai-endpoint`
   - `azure-openai-api-key`
   - `azure-openai-deployment`
3. Restart web app and retry.

### 4) Continue to Lab 2
Use `labs/lab2-rag-policy-bot/LAB.md` and follow **CLASS mode** sections only.

---

## Rules to avoid confusion
- If `$RG/$KV/$APP` already exist: **do not recreate them**.
- In PowerShell, use `$VAR = "value"` (not `export`).
- Key Vault secret names use dashes, not underscores.

## Instructor delivery pattern (recommended)
For each command block in class:
- 1 sentence: *why this command exists*
- run command
- 1 visible checkpoint

Example:
- Why: "We wire app settings to Key Vault so secrets never live in code."
- Command: `az webapp config appsettings set ...`
- Checkpoint: App Settings show Key Vault references.
