# Lab 1 — AI Intake Assistant (Document → JSON → Workflow)

> Running this as a live class? Start with `docs/CLASS_FAST_PATH.md` and use this file as supporting detail.

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

## Prerequisites — two delivery modes

### A) Class mode (recommended for live training)
Use this during class to maximize hands-on lab time.

**Instructor pre-provisions (before class):**
- Azure OpenAI resource + deployed model
- (Optional) Document Intelligence resource
- Subscription guardrails (budget/quota/policies)
- Optional participant RG baseline (or deploy via `infra/iac`)

**Participants do in class:**
- `az login` + access check
- Run local app and lab code
- Create/deploy Web App + Managed Identity + Key Vault wiring

### B) Self-serve mode (for later reference / homework)
Participants set up everything end-to-end themselves using:
- [`infra/RESOURCE_SETUP.md`](../../infra/RESOURCE_SETUP.md)
- [`infra/iac/README.md`](../../infra/iac/README.md)

This keeps class fast while preserving full reproducibility afterward.

---

## Step 0 — Access check + resource group
Pick a region (recommend **westeurope**).

> **Class mode:** If instructor already provided `$RG`, reuse it and skip RG creation.

### PowerShell (Windows)
```powershell
az login
az account show

$LOCATION = "westeurope"
if (-not $RG) { $RG = "rg-azure-ai-workshop-$(Get-Random)" }
az group create -n $RG -l $LOCATION
```

### Bash (WSL/macOS/Linux)
```bash
az login
az account show

export LOCATION=westeurope
export RG=${RG:-rg-azure-ai-workshop-$RANDOM}
az group create -n $RG -l $LOCATION
```

**Checkpoint:** `az group show -n $RG` works.

> 📸 **Screenshot suggestion (L1-S01):** Azure Portal showing the new Resource Group overview (`$RG`) with region visible.

---

## Step 1 — Create Key Vault (secrets live here)
```bash
export KV=kv-aiws-$RANDOM
az keyvault create -g $RG -n $KV -l $LOCATION
```

Add secrets (names are examples):
- `azure-openai-endpoint`
- `azure-openai-api-key` (if you cannot use MI for AOAI; many orgs still use key)
- `azure-openai-deployment`
- (Optional) `docintel-endpoint`
- (Optional) `docintel-api-key`

```bash
az keyvault secret set --vault-name $KV -n azure-openai-endpoint --value "https://<your-aoai>.openai.azure.com/"
az keyvault secret set --vault-name $KV -n azure-openai-api-key --value "<key>"
az keyvault secret set --vault-name $KV -n azure-openai-deployment --value "<deployment-name>"
```

**Checkpoint:** you can retrieve one secret:
```bash
az keyvault secret show --vault-name $KV -n azure-openai-deployment --query value -o tsv
```

> 📸 **Screenshot suggestion (L1-S02):** Key Vault Secrets list showing required secret names (mask values).

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

> 📸 **Screenshot suggestion (L1-S03):** Terminal output with a successful `POST /intake` response showing valid JSON.

---

## Step 3 — (Optional) Document Intelligence extraction
If available:
- Upload a sample PDF/image
- Extract text and/or key fields
- Feed extracted text into the LLM normalization step

If not available:
- Use a plain `.txt` sample or a pasted text snippet

> 📸 **Screenshot suggestion (L1-S04):** Document extraction output preview (raw extracted text or extracted fields), with any sensitive content removed.

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

> 📸 **Screenshot suggestion (L1-S05):** Web App Identity page + RBAC assignment (`Key Vault Secrets User`) confirmation.

---

## Step 5 — Configure Key Vault references in App Settings
Set settings to Key Vault references (App Service supports `@Microsoft.KeyVault(...)`).

> If you just finished `infra/RESOURCE_SETUP.md` Phase 5, this is your immediate next step.

Example:
```bash
az webapp config appsettings set -g $RG -n $APP --settings \
  AZURE_OPENAI_ENDPOINT="@Microsoft.KeyVault(SecretUri=https://$KV.vault.azure.net/secrets/azure-openai-endpoint/)" \
  AZURE_OPENAI_API_KEY="@Microsoft.KeyVault(SecretUri=https://$KV.vault.azure.net/secrets/azure-openai-api-key/)" \
  AZURE_OPENAI_DEPLOYMENT="@Microsoft.KeyVault(SecretUri=https://$KV.vault.azure.net/secrets/azure-openai-deployment/)"
```

**Checkpoint:** In Azure Portal → Web App → Configuration, values show as Key Vault references (not plain text).

> 📸 **Screenshot suggestion (L1-S06):** Web App Configuration page showing Key Vault reference format for app settings.

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

> 📸 **Screenshot suggestion (L1-S07):** Live `/docs` Swagger page for deployed app.

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
