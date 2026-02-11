# Reproducible Path — Lab 1 to Working AI Intake (Windows PowerShell)

Use this exact sequence to reach a fully functional AOAI-backed `/intake` endpoint.

## Scope
- Target: `labs/lab1-intake-assistant`
- Requirement: `POST /intake` must return AI-generated JSON (hard-fail if AOAI is broken)

## 0) Preconditions
- Azure CLI installed and logged in
- Subscription selected
- Existing RG, KV, App Service Plan, Web App
- AOAI resource exists in same subscription

## 1) Required variable values (PowerShell)
```powershell
$RG = "rg-aiws-159277257"
$KV = "kv-aiws-159277257"
$PLAN = "plan-aiws-159277257"
$APP = "app-aiws-1831894484"
$AOAI = "aoai-aiws-159277257"
$LOCATION = "westeurope"
$AOAI_DEPLOYMENT = "gpt4omini"
```

## 2) Ensure AOAI deployment exists
```powershell
az cognitiveservices account deployment create `
  -g $RG -n $AOAI `
  --deployment-name $AOAI_DEPLOYMENT `
  --model-name gpt-4o-mini `
  --model-version "2024-07-18" `
  --model-format OpenAI `
  --sku-name GlobalStandard --sku-capacity 1
```

## 3) Set Key Vault secrets (dash names)
```powershell
$AOAI_ENDPOINT = az cognitiveservices account show -g $RG -n $AOAI --query properties.endpoint -o tsv
$AOAI_KEY = az cognitiveservices account keys list -g $RG -n $AOAI --query key1 -o tsv

az keyvault secret set --vault-name $KV -n azure-openai-endpoint --value "$AOAI_ENDPOINT"
az keyvault secret set --vault-name $KV -n azure-openai-api-key --value "$AOAI_KEY"
az keyvault secret set --vault-name $KV -n azure-openai-deployment --value "$AOAI_DEPLOYMENT"
```

## 4) Wire app settings on Web App
```powershell
az webapp config appsettings set -g $RG -n $APP --settings `
  WEBSITE_RUN_FROM_PACKAGE=0 `
  SCM_DO_BUILD_DURING_DEPLOYMENT=true `
  AZURE_OPENAI_ENDPOINT="@Microsoft.KeyVault(SecretUri=https://$KV.vault.azure.net/secrets/azure-openai-endpoint/)" `
  AZURE_OPENAI_API_KEY="@Microsoft.KeyVault(SecretUri=https://$KV.vault.azure.net/secrets/azure-openai-api-key/)" `
  AZURE_OPENAI_DEPLOYMENT="@Microsoft.KeyVault(SecretUri=https://$KV.vault.azure.net/secrets/azure-openai-deployment/)"
```

## 5) Wait, then deploy
```powershell
Start-Sleep -Seconds 45
cd C:\Users\lennertvhoy\azure-ai-one-day-workshop
git pull
cd .\labs\lab1-intake-assistant
az webapp up -g $RG -n $APP -l $LOCATION --runtime "PYTHON:3.11"
```

## 6) Mandatory validation (must pass)
```powershell
curl https://$APP.azurewebsites.net/health
```
Expected:
```json
{"ok":true}
```

Open in browser:
- `https://$APP.azurewebsites.net/docs`
- Run `POST /intake` with:
```json
{"text":"Invoice INV-001 from Contoso Office Supplies for EUR 1,250.00 due in 14 days."}
```
Expected: JSON including `doc_type`, `entities`, `summary`, `routing`.

## 7) If `POST /intake` returns 500
Check these in order:
1. AOAI deployment exists and name matches secret (`gpt4omini`).
2. Key Vault secret names use dashes (not underscores).
3. Web App app settings point to Key Vault references.
4. Wait 30–60s after config changes before redeploy/restart.
5. Do not run config/restart/deploy operations in parallel.
