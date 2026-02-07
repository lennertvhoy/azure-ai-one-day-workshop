# Lab 1 — AI Intake Assistant (Document → JSON → Workflow)

## Goal
Build a GDPR-safe **Python** app that:
1) extracts text/fields from a document (invoice / report)
2) uses **Azure OpenAI** to normalize + enrich into **structured JSON**
3) stores output and exposes results via a simple web UI
4) deploys to **Azure Web App** using **Managed Identity + Key Vault**

## Timebox
- Build (local): ~90 minutes
- Deploy to Web App: ~45 minutes

## Architecture (thin slice)
- UI: Streamlit (local) OR simple FastAPI endpoint (recommended for Web App)
- Extraction: **Document Intelligence** (preferred) or OCR/text fallback
- LLM: Azure OpenAI Chat Completions
- Secrets: Key Vault
- Hosting: Azure Web App (Linux)

---

## Prerequisites
- Azure subscription permissions (create RG, Web App, Key Vault)
- Azure OpenAI resource + deployed model (e.g., `gpt-4o-mini` or equivalent)
- (Optional) Azure AI Document Intelligence resource
- Local: Python 3.11+, `az` CLI

---

## Step 0 — Create resource group + set defaults
Pick a region (recommend **westeurope**).

```bash
az login
az account show

export LOCATION=westeurope
export RG=rg-azure-ai-workshop-$RANDOM
az group create -n $RG -l $LOCATION
```

**Checkpoint:** `az group show -n $RG` works.

---

## Step 1 — Create Key Vault (secrets live here)
```bash
export KV=kv-aiws-$RANDOM
az keyvault create -g $RG -n $KV -l $LOCATION
```

Add secrets (names are examples):
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY` (if you cannot use MI for AOAI; many orgs still use key)
- `AZURE_OPENAI_DEPLOYMENT`
- (Optional) `DOCINTEL_ENDPOINT`
- (Optional) `DOCINTEL_API_KEY`

```bash
az keyvault secret set --vault-name $KV -n AZURE_OPENAI_ENDPOINT --value "https://<your-aoai>.openai.azure.com/"
az keyvault secret set --vault-name $KV -n AZURE_OPENAI_API_KEY --value "<key>"
az keyvault secret set --vault-name $KV -n AZURE_OPENAI_DEPLOYMENT --value "<deployment-name>"
```

**Checkpoint:** you can retrieve one secret:
```bash
az keyvault secret show --vault-name $KV -n AZURE_OPENAI_DEPLOYMENT --query value -o tsv
```

---

## Step 2 — Local app (thin slice)
Create a virtualenv:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install fastapi uvicorn azure-identity azure-keyvault-secrets azure-ai-formrecognizer openai pydantic
```

### Minimal API contract
We want an endpoint:
- `POST /intake` with a text payload (we start with text to keep it moving)
- returns JSON with fields and a summary

Create `app/main.py`:
- load secrets from environment for local
- call Azure OpenAI with a strict JSON schema instruction

**Prompt contract (example JSON):**
```json
{
  "doc_type": "invoice|incident_report|policy|unknown",
  "entities": {"vendor": "...", "invoice_number": "..."},
  "summary": "...",
  "routing": {"team": "Finance|IT|HR|Unknown", "priority": "low|medium|high"}
}
```

**Checkpoint:** `curl` returns valid JSON.

---

## Step 3 — (Optional) Document Intelligence extraction
If available:
- Upload a sample PDF/image
- Extract text and/or key fields
- Feed extracted text into the LLM normalization step

If not available:
- Use a plain `.txt` sample or a pasted text snippet

---

## Step 4 — Create Azure Web App (Linux)
```bash
export APP=app-aiws-intake-$RANDOM
az appservice plan create -g $RG -n plan-aiws --is-linux --sku B1
az webapp create -g $RG -p plan-aiws -n $APP --runtime "PYTHON|3.11"
```

Enable managed identity:
```bash
az webapp identity assign -g $RG -n $APP
export MI_PRINCIPAL_ID=$(az webapp identity show -g $RG -n $APP --query principalId -o tsv)
```

Grant Key Vault access (RBAC preferred):
```bash
export KV_ID=$(az keyvault show -g $RG -n $KV --query id -o tsv)
az role assignment create --assignee-object-id $MI_PRINCIPAL_ID \
  --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets User" \
  --scope $KV_ID
```

**Checkpoint:** role assignment exists.

---

## Step 5 — Configure Key Vault references in App Settings
Set settings to Key Vault references (App Service supports `@Microsoft.KeyVault(...)`).
Example:
```bash
az webapp config appsettings set -g $RG -n $APP --settings \
  AZURE_OPENAI_ENDPOINT="@Microsoft.KeyVault(SecretUri=https://$KV.vault.azure.net/secrets/AZURE_OPENAI_ENDPOINT/)" \
  AZURE_OPENAI_API_KEY="@Microsoft.KeyVault(SecretUri=https://$KV.vault.azure.net/secrets/AZURE_OPENAI_API_KEY/)" \
  AZURE_OPENAI_DEPLOYMENT="@Microsoft.KeyVault(SecretUri=https://$KV.vault.azure.net/secrets/AZURE_OPENAI_DEPLOYMENT/)"
```

**Checkpoint:** In Azure Portal → Web App → Configuration, values show as Key Vault references (not plain text).

---

## Step 6 — Deploy code
You can deploy via:
- `az webapp up` (simple)
- GitHub Actions (more enterprise)

For class speed, use:
```bash
az webapp up -g $RG -n $APP -l $LOCATION --runtime "PYTHON|3.11"
```

**Checkpoint:** `https://$APP.azurewebsites.net/docs` loads (if FastAPI).

---

## Success criteria
- App runs locally and in Azure.
- No secrets committed to repo.
- App can process at least **2 sample docs** end-to-end.
- Output is valid JSON and stable across retries.

## Stretch goals
- Add retry + timeout handling
- Add logging with redaction
- Add a “human approval” step before routing
