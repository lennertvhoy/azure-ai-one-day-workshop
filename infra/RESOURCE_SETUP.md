# Infra — Resource Setup (Trainer / Participants)

This guide now supports both **Windows PowerShell** and **WSL/Bash**.

## Which document should you follow?
- **`README.md`** → local machine bootstrap (Git clone, setup scripts, verify).
- **`infra/RESOURCE_SETUP.md` (this file)** → Azure resource provisioning (manual `az` path).
- **`infra/iac/README.md`** → preferred IaC path (repeatable for cohorts).

If you want complete setup knowledge, use all three in this order:
1) `README.md`
2) `infra/iac/README.md` (preferred provisioning path)
3) `infra/RESOURCE_SETUP.md` (manual `az` fallback/reference)

Important naming note:
- Key Vault secret names must use only letters/numbers/dashes (no underscores).
- App setting keys can still use underscores (e.g. `AZURE_OPENAI_ENDPOINT`).
- Example: `DOCINTEL_ENDPOINT` (env var) maps to `docintel-endpoint` (Key Vault secret name).

---

## Recommended region
- **westeurope** (Belgium-friendly)

---

## Phase 1 — Local environment

## A) Windows (PowerShell, recommended for class)
Use the repo setup scripts first:

```powershell
git clone https://github.com/lennertvhoy/azure-ai-one-day-workshop.git
cd azure-ai-one-day-workshop
powershell -ExecutionPolicy Bypass -File .\scripts\setup\setup-all.ps1
```

Then login/select subscription:

```powershell
az login
az account show
az account list -o table
az account set --subscription "<SUBSCRIPTION_NAME_OR_ID>"
```

Generate unique per-student names (recommended for multi-student cohorts):

```powershell
# copy/paste (change StudentCode)
powershell -ExecutionPolicy Bypass -File .\infra\iac\student-vars.ps1 -StudentCode p01 -WriteFile
# optional: load generated vars into current shell
. .\.student-vars.p01.ps1
```

### B) Ubuntu on WSL (optional path)
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip jq git curl
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

az login
az account show
az account list -o table
az account set --subscription "<SUBSCRIPTION_NAME_OR_ID>"
```

**Checkpoint:** `az account show` works and points to intended tenant/subscription.

---

## Phase 2 — Core infrastructure (manual `az` path)

### Naming convention (example)
- RG: `rg-aiws-<name>`
- KV: `kv-aiws-<name>`
- WebApp: `app-aiws-<name>`
- Search: `srch-aiws-<name>`

### PowerShell commands
```powershell
$LOCATION = "westeurope"
$SUFFIX = Get-Random
$RG = "rg-aiws-$SUFFIX"
$KV = "kv-aiws-$SUFFIX"
$PLAN = "plan-aiws-$SUFFIX"
$APP = "app-aiws-$SUFFIX"

az group create --name $RG --location $LOCATION

az keyvault create `
  --name $KV `
  --resource-group $RG `
  --location $LOCATION `
  --enable-rbac-authorization true

az appservice plan create --name $PLAN --resource-group $RG --sku B1 --is-linux
az webapp create --name $APP --resource-group $RG --plan $PLAN --runtime "PYTHON:3.11"
```

> Note (Windows PowerShell): use `PYTHON:3.11`. Some shells mis-handle `PYTHON|3.11`.

### Bash commands (WSL)
```bash
export LOCATION=westeurope
export RG=rg-aiws-$RANDOM
export KV=kv-aiws-$RANDOM
export PLAN=plan-aiws-$RANDOM
export APP=app-aiws-$RANDOM

az group create --name $RG --location $LOCATION

az keyvault create \
  --name $KV \
  --resource-group $RG \
  --location $LOCATION \
  --enable-rbac-authorization true

az appservice plan create --name $PLAN --resource-group $RG --sku B1 --is-linux
az webapp create --name $APP --resource-group $RG --plan $PLAN --runtime "PYTHON|3.11"
```

---

## Phase 3 — Azure OpenAI (resource + model deployment)
> Many tenants require approval for Azure OpenAI. For workshops, pre-provisioning is strongly recommended.

### What is copy/paste vs fill in?
- ✅ **Copy/paste directly:** all commands below.
- ✍️ **Fill in / choose:** model + deployment settings if your region/tenant doesn’t support defaults.

### PowerShell (manual path)
```powershell
# Copy/paste
$AOAI = "aoai-aiws-$SUFFIX"
$AOAI_DEPLOYMENT = "gpt4omini"   # you can rename this

az cognitiveservices account create `
  --name $AOAI `
  --resource-group $RG `
  --location $LOCATION `
  --kind OpenAI `
  --sku S0

# Try this first (commonly works):
az cognitiveservices account deployment create `
  --name $AOAI `
  --resource-group $RG `
  --deployment-name $AOAI_DEPLOYMENT `
  --model-name gpt-4o-mini `
  --model-version "2024-07-18" `
  --model-format OpenAI `
  --sku-name "GlobalStandard"

# If deployment fails in your region/tenant:
# 1) Create the model deployment in Azure AI Foundry/Portal
# 2) Keep using the deployment name you created in $AOAI_DEPLOYMENT

$AOAI_ENDPOINT = "https://$AOAI.openai.azure.com"
$AOAI_KEY = az cognitiveservices account keys list -g $RG -n $AOAI --query key1 -o tsv

# Key Vault secret names use dashes (not underscores)
az keyvault secret set --vault-name $KV -n azure-openai-endpoint --value "$AOAI_ENDPOINT"
az keyvault secret set --vault-name $KV -n azure-openai-deployment --value "$AOAI_DEPLOYMENT"
az keyvault secret set --vault-name $KV -n azure-openai-api-key --value "$AOAI_KEY"
```

### Bash (manual path)
```bash
# Copy/paste
export AOAI=aoai-aiws-$RANDOM
export AOAI_DEPLOYMENT=gpt4omini

az cognitiveservices account create \
  --name $AOAI \
  --resource-group $RG \
  --location $LOCATION \
  --kind OpenAI \
  --sku S0

az cognitiveservices account deployment create \
  --name $AOAI \
  --resource-group $RG \
  --deployment-name $AOAI_DEPLOYMENT \
  --model-name gpt-4o-mini \
  --model-version "2024-07-18" \
  --model-format OpenAI \
  --sku-name "GlobalStandard"

# If deployment fails: create deployment in Portal and keep AOAI_DEPLOYMENT aligned.

export AOAI_ENDPOINT="https://$AOAI.openai.azure.com"
export AOAI_KEY=$(az cognitiveservices account keys list -g $RG -n $AOAI --query key1 -o tsv)

# Key Vault secret names use dashes (not underscores)
az keyvault secret set --vault-name $KV -n azure-openai-endpoint --value "$AOAI_ENDPOINT"
az keyvault secret set --vault-name $KV -n azure-openai-deployment --value "$AOAI_DEPLOYMENT"
az keyvault secret set --vault-name $KV -n azure-openai-api-key --value "$AOAI_KEY"
```

---

## Phase 4 — (Optional) Document Intelligence
### PowerShell
```powershell
$DOCINTEL = "docintel-aiws-$SUFFIX"

az cognitiveservices account create `
  --name $DOCINTEL `
  --resource-group $RG `
  --location $LOCATION `
  --kind FormRecognizer `
  --sku F0

$DOCINTEL_ENDPOINT = az cognitiveservices account show -g $RG -n $DOCINTEL --query properties.endpoint -o tsv
$DOCINTEL_KEY = az cognitiveservices account keys list -g $RG -n $DOCINTEL --query key1 -o tsv

az keyvault secret set --vault-name $KV -n docintel-endpoint --value "$DOCINTEL_ENDPOINT"
az keyvault secret set --vault-name $KV -n docintel-api-key --value "$DOCINTEL_KEY"
```

### Bash
```bash
export DOCINTEL=docintel-aiws-$RANDOM
az cognitiveservices account create \
  --name $DOCINTEL \
  --resource-group $RG \
  --location $LOCATION \
  --kind FormRecognizer \
  --sku F0

export DOCINTEL_ENDPOINT=$(az cognitiveservices account show -g $RG -n $DOCINTEL --query properties.endpoint -o tsv)
export DOCINTEL_KEY=$(az cognitiveservices account keys list -g $RG -n $DOCINTEL --query key1 -o tsv)

az keyvault secret set --vault-name $KV -n docintel-endpoint --value "$DOCINTEL_ENDPOINT"
az keyvault secret set --vault-name $KV -n docintel-api-key --value "$DOCINTEL_KEY"
```

---

## Phase 5 — Permissions & identity (crucial)

### PowerShell
```powershell
az webapp identity assign --name $APP --resource-group $RG
$MI_PRINCIPAL_ID = az webapp identity show -g $RG -n $APP --query principalId -o tsv
$KV_ID = az keyvault show -g $RG -n $KV --query id -o tsv

az role assignment create `
  --assignee-object-id $MI_PRINCIPAL_ID `
  --assignee-principal-type ServicePrincipal `
  --role "Key Vault Secrets User" `
  --scope $KV_ID
```

### Bash
```bash
az webapp identity assign --name $APP --resource-group $RG
export MI_PRINCIPAL_ID=$(az webapp identity show -g $RG -n $APP --query principalId -o tsv)
export KV_ID=$(az keyvault show -g $RG -n $KV --query id -o tsv)

az role assignment create \
  --assignee-object-id $MI_PRINCIPAL_ID \
  --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets User" \
  --scope $KV_ID
```

(Optional / tenant-dependent) Azure OpenAI RBAC:
- Role: `Cognitive Services OpenAI User` on AOAI resource

---

## Common gotchas (quick fixes)
- **`BadParameter ... invalid name` when setting Key Vault secret**
  - Cause: underscores in secret name.
  - Fix: use dash names (`azure-openai-endpoint`, `docintel-endpoint`, etc.).
- **`ForbiddenByRbac` when setting Key Vault secret**
  - Cause: missing RBAC role on Key Vault.
  - Fix: assign `Key Vault Secrets Officer` (or equivalent) and wait for propagation.
- **AOAI deployment SKU/model not supported in region**
  - Cause: regional model/SKU availability differences.
  - Fix: use Portal/Foundry deployment fallback and keep deployment name aligned in variables.

## Recommended for paid course operations
- Prefer **IaC** for cohorts: `infra/iac/README.md`
- Keep manual `az` steps as reference and fallback
- Use small SKUs + tags + expiry cleanup

---

## Budget-friendly defaults
- App Service plan: `B1`
- AI Search: `basic`

---

## Provider registration quickstart
### PowerShell
```powershell
az provider register --namespace Microsoft.CognitiveServices
az provider register --namespace Microsoft.Search
az provider register --namespace Microsoft.Web
az provider register --namespace Microsoft.KeyVault
```

### Bash
```bash
az provider register --namespace Microsoft.CognitiveServices
az provider register --namespace Microsoft.Search
az provider register --namespace Microsoft.Web
az provider register --namespace Microsoft.KeyVault
```
