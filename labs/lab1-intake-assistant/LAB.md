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

### Class mode quick navigation (important)
If instructor already gave you `$RG`, `$KV`, `$APP` and AOAI secrets in Key Vault:
- Step 0: **Access check only** (skip RG create)
- Step 1: **Skip** (KV/secrets already done)
- Step 2: Run **Track A** (local smoke) or **Track B** (full local) 
- Step 3: **Skip for first pass**
- Step 4: **Skip** (Web App already exists)
- Step 5: **Do this** (wire app settings to Key Vault)
- Step 6: **Do this** (deploy app code)

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
> Class mode: skip if instructor already provided `$KV` and the required secrets.

### PowerShell (Windows)
```powershell
if (-not $KV) { $KV = "kv-aiws-$(Get-Random)" }
az keyvault create -g $RG -n $KV -l $LOCATION
```

### Bash (WSL/macOS/Linux)
```bash
export KV=${KV:-kv-aiws-$RANDOM}
az keyvault create -g $RG -n $KV -l $LOCATION
```

Add secrets (names are examples):
- `azure-openai-endpoint`
- `azure-openai-api-key` (if you cannot use MI for AOAI; many orgs still use key)
- `azure-openai-deployment`
- (Optional) `docintel-endpoint`
- (Optional) `docintel-api-key`

```powershell
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
Create a virtualenv.

### PowerShell (Windows)
```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r .\labs\lab1-intake-assistant\requirements.txt
```

If activation is blocked or you prefer no activation:
```powershell
.\.venv\Scripts\python.exe -m pip install -r .\labs\lab1-intake-assistant\requirements.txt
```

### Bash (WSL/macOS/Linux)
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r ./labs/lab1-intake-assistant/requirements.txt
```

### What to do after install (pick one track)

#### Track A — **Class default (recommended): smoke test only**
Goal: verify app starts locally without spending time on local cloud auth.

```powershell
cd .\labs\lab1-intake-assistant
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` and confirm docs load.
Then stop (`Ctrl+C`) and continue to **Step 5** and **Step 6** for full cloud functionality.

#### Track B — **Optional full local functionality**
Goal: make `POST /intake` work locally before deployment.

1) Create local env file using:
- `labs/lab1-intake-assistant/app/ENV_EXAMPLE.md` (copy values into `labs/lab1-intake-assistant/app/.env`)

2) Fill values in `.env`:
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_DEPLOYMENT`

3) Run app and test `POST /intake` from `/docs`.

**Prompt contract (example JSON):**
```json
{
  "doc_type": "invoice|incident_report|policy|unknown",
  "entities": {"vendor": "...", "invoice_number": "..."},
  "summary": "...",
  "routing": {"team": "Finance|IT|HR|Unknown", "priority": "low|medium|high"}
}
```

**Checkpoint options:**
- Track A: `/docs` loads locally
- Track B: `POST /intake` returns valid JSON

> 📸 **Screenshot suggestion (L1-S03):** Terminal output with app running and (if Track B) successful `POST /intake` JSON response.

---

## Step 3 — (Optional) Document Intelligence extraction
> Class default: skip this in first pass; return after deployed flow works.

If available:
- Upload a sample PDF/image
- Extract text and/or key fields
- Feed extracted text into the LLM normalization step

If not available:
- Use a plain `.txt` sample or a pasted text snippet

> 📸 **Screenshot suggestion (L1-S04):** Document extraction output preview (raw extracted text or extracted fields), with any sensitive content removed.

---

## Step 4 — Create Azure Web App (Linux)
> Class mode: skip if instructor already provided `$APP` and App Service plan.

### PowerShell (Windows)
```powershell
if (-not $APP) { $APP = "app-aiws-intake-$(Get-Random)" }
az appservice plan create -g $RG -n plan-aiws --is-linux --sku B1
az webapp create -g $RG -p plan-aiws -n $APP --runtime "PYTHON:3.11"
```

### Bash (WSL/macOS/Linux)
```bash
export APP=${APP:-app-aiws-intake-$RANDOM}
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

Example (PowerShell):
```powershell
az webapp config appsettings set -g $RG -n $APP --settings `
  AZURE_OPENAI_ENDPOINT="@Microsoft.KeyVault(SecretUri=https://$KV.vault.azure.net/secrets/azure-openai-endpoint/)" `
  AZURE_OPENAI_API_KEY="@Microsoft.KeyVault(SecretUri=https://$KV.vault.azure.net/secrets/azure-openai-api-key/)" `
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

### PowerShell (Windows)
```powershell
az webapp up -g $RG -n $APP -l $LOCATION --runtime "PYTHON:3.11"
```

### Bash (WSL/macOS/Linux)
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
