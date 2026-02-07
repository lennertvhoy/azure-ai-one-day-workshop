# Infra — Resource Setup (Trainer / Participants)

## Recommended region
- **westeurope** (Belgium-friendly)

---

## Phase 1 — Local environment (Ubuntu on WSL)
These steps are written to work on **Ubuntu WSL**.

### 1) Python 3.11+
On Ubuntu:
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
python3 --version
```

Create/activate venv (per lab folder):
```bash
python3 -m venv .venv
source .venv/bin/activate
python -V
```

### 2) Azure CLI (`az`) on Ubuntu
Microsoft install script:
```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
az version
```

Login + choose subscription:
```bash
az login
az account show
# If you have multiple subscriptions:
az account list -o table
az account set --subscription "<SUBSCRIPTION_NAME_OR_ID>"
```

### 3) Useful tools
```bash
sudo apt install -y jq git curl
```

**Checkpoint:** `az account show` works and shows the intended tenant/subscription.

---

## Phase 2 — Core Infrastructure (RG, Key Vault, Web App)
We use a single resource group to keep everything organized.

### Naming convention (example)
- RG: `rg-aiws-<name>`
- KV: `kv-aiws-<name>`
- WebApp: `app-aiws-<name>`
- Search: `srch-aiws-<name>`

### 1) Create Resource Group (RG)
```bash
export LOCATION=westeurope
export RG=rg-aiws-$RANDOM
az group create --name $RG --location $LOCATION
```

### 2) Create Azure Key Vault (RBAC mode)
Use RBAC instead of access policies:
```bash
export KV=kv-aiws-$RANDOM
az keyvault create \
  --name $KV \
  --resource-group $RG \
  --location $LOCATION \
  --enable-rbac-authorization true
```

### 3) Create Web App (App Service)
Create a plan first, then the web app.
```bash
export PLAN=plan-aiws
export APP=app-aiws-$RANDOM

az appservice plan create --name $PLAN --resource-group $RG --sku B1 --is-linux
az webapp create --name $APP --resource-group $RG --plan $PLAN --runtime "PYTHON|3.11"
```

---

## Phase 3 — Azure OpenAI (resource + model deployment)
> Note: Many tenants require approval for Azure OpenAI. For workshops, pre-provisioning is recommended.

### 1) Create Azure OpenAI resource
```bash
export AOAI=aoai-aiws-$RANDOM
az cognitiveservices account create \
  --name $AOAI \
  --resource-group $RG \
  --location $LOCATION \
  --kind OpenAI \
  --sku S0
```

### 2) Deploy a model (example: gpt-4o-mini)
```bash
export AOAI_DEPLOYMENT=gpt-4o-mini

az cognitiveservices account deployment create \
  --name $AOAI \
  --resource-group $RG \
  --deployment-name $AOAI_DEPLOYMENT \
  --model-name gpt-4o-mini \
  --model-version "2024-07-18" \
  --model-format OpenAI \
  --sku-capacity 10 \
  --sku-name "Standard"
```

Store your endpoint + deployment in Key Vault (and API key if needed):
```bash
export AOAI_ENDPOINT="https://$AOAI.openai.azure.com"
export AOAI_KEY=$(az cognitiveservices account keys list -g $RG -n $AOAI --query key1 -o tsv)

az keyvault secret set --vault-name $KV -n AZURE_OPENAI_ENDPOINT --value "$AOAI_ENDPOINT"
az keyvault secret set --vault-name $KV -n AZURE_OPENAI_DEPLOYMENT --value "$AOAI_DEPLOYMENT"
az keyvault secret set --vault-name $KV -n AZURE_OPENAI_API_KEY --value "$AOAI_KEY"
```

---

## Phase 4 — (Optional) Document Intelligence
If you want PDF/image extraction:
```bash
export DOCINTEL=docintel-aiws-$RANDOM
az cognitiveservices account create \
  --name $DOCINTEL \
  --resource-group $RG \
  --location $LOCATION \
  --kind FormRecognizer \
  --sku F0
```

Store secrets:
```bash
export DOCINTEL_ENDPOINT=$(az cognitiveservices account show -g $RG -n $DOCINTEL --query properties.endpoint -o tsv)
export DOCINTEL_KEY=$(az cognitiveservices account keys list -g $RG -n $DOCINTEL --query key1 -o tsv)

az keyvault secret set --vault-name $KV -n DOCINTEL_ENDPOINT --value "$DOCINTEL_ENDPOINT"
az keyvault secret set --vault-name $KV -n DOCINTEL_API_KEY --value "$DOCINTEL_KEY"
```

---

## Phase 5 — Permissions & Identity (crucial)
### 1) Enable Managed Identity on the Web App
```bash
az webapp identity assign --name $APP --resource-group $RG
export MI_PRINCIPAL_ID=$(az webapp identity show -g $RG -n $APP --query principalId -o tsv)
```

### 2) Assign roles
Key Vault: allow the app to read secrets
```bash
export KV_ID=$(az keyvault show -g $RG -n $KV --query id -o tsv)
az role assignment create \
  --assignee-object-id $MI_PRINCIPAL_ID \
  --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets User" \
  --scope $KV_ID
```

(Optional / tenant-dependent) Azure OpenAI RBAC:
- Role: `Cognitive Services OpenAI User` on the Azure OpenAI resource

---

## Budget-friendly defaults
- App Service plan: `B1` for class
- AI Search: `basic`

---

## Az CLI quickstart (providers)
```bash
az provider register --namespace Microsoft.CognitiveServices
az provider register --namespace Microsoft.Search
az provider register --namespace Microsoft.Web
az provider register --namespace Microsoft.KeyVault
```
