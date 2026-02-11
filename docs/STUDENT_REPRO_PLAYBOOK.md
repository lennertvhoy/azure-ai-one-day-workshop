# Student Repro Playbook (Windows, End-to-End)

This is the canonical, reproducible student path for the full workshop outcome.

## Outcome
By the end, students will have:
1) Lab 1 API deployed and working (`/intake`)
2) Lab 2 API deployed and working (`/chat` + citations)
3) Optional connected pipeline (Lab1 -> Lab2 index)
4) Optional demo GUI

---

## 0) Prerequisites
- Windows PowerShell
- Python 3.11+
- Azure CLI
- Git
- Azure subscription access (see `docs/ACCESS_REQUIREMENTS.md`)

Clone:
```powershell
git clone https://github.com/lennertvhoy/azure-ai-one-day-workshop.git
cd azure-ai-one-day-workshop
```

---

## 1) Shared variables (set once)
```powershell
$RG = "rg-aiws-159277257"
$KV = "kv-aiws-159277257"
$PLAN = "plan-aiws-159277257"
$LOCATION = "westeurope"
$AOAI = "aoai-aiws-159277257"

$APP = "app-aiws-1831894484"          # Lab 1 app
$APP2 = "app-aiws-rag-159277257"      # Lab 2 app
$SEARCH = "srch-aiws-1406684866"      # Lab 2 search
```

Log in + verify:
```powershell
az login
az account show
```

---

## 2) Lab 1 (AI Intake API)
Follow:
- `docs/REPRODUCIBLE_PATH.md`

Must pass:
- `https://$APP.azurewebsites.net/health`
- `https://$APP.azurewebsites.net/docs`
- `POST /intake` returns structured JSON

---

## 3) Lab 2 Step 0/1 (Search + Index)
Follow:
- `labs/lab2-rag-policy-bot/LAB.md` Step 0 and Step 1 (PowerShell blocks)

Important:
- run from `labs/lab2-rag-policy-bot`
- in PowerShell, do **not** use bash `curl -X/-H/-d`; use `Invoke-RestMethod`

---

## 4) Lab 2 Step 2/3 (Ingest + Local Chat)
```powershell
cd .\labs\lab2-rag-policy-bot
pip install -r requirements.txt

$SEARCH_ADMIN_KEY = az search admin-key show --resource-group $RG --service-name $SEARCH --query primaryKey -o tsv
$SEARCH_ENDPOINT = "https://$SEARCH.search.windows.net"

$env:SEARCH_ENDPOINT = $SEARCH_ENDPOINT
$env:SEARCH_ADMIN_KEY = $SEARCH_ADMIN_KEY
python .\ingest.py --data .\data --index policy-index

$env:AZURE_OPENAI_ENDPOINT = az keyvault secret show --vault-name $KV -n azure-openai-endpoint --query value -o tsv
$env:AZURE_OPENAI_API_KEY = az keyvault secret show --vault-name $KV -n azure-openai-api-key --query value -o tsv
$env:AZURE_OPENAI_DEPLOYMENT = az keyvault secret show --vault-name $KV -n azure-openai-deployment --query value -o tsv
$env:SEARCH_API_KEY = $env:SEARCH_ADMIN_KEY
$env:SEARCH_INDEX = "policy-index"

uvicorn app.main:app --reload --port 8002
```

In another terminal:
```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8002/chat" -ContentType "application/json" -Body '{"question":"When should I report phishing?"}'
```

---

## 5) Lab 2 Step 4 (Deploy Web App)
Follow Step 4 in:
- `labs/lab2-rag-policy-bot/LAB.md`

Use fallback 4.4B if RBAC assignment is blocked.

After deploy, set startup command (required):
```powershell
az webapp config set -g $RG -n $APP2 --startup-file "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
az webapp restart -g $RG -n $APP2
Start-Sleep -Seconds 20
```

Validate:
- `https://$APP2.azurewebsites.net/health`
- `https://$APP2.azurewebsites.net/docs`
- `POST /chat` returns answer + citations

---

## 6) Optional enterprise bridge (recommended)
```powershell
cd .\labs\lab2-rag-policy-bot
$env:LAB1_URL = "https://$APP.azurewebsites.net"
$env:SEARCH_ENDPOINT = az keyvault secret show --vault-name $KV -n search-endpoint --query value -o tsv
$env:SEARCH_ADMIN_KEY = az keyvault secret show --vault-name $KV -n search-admin-key --query value -o tsv
$env:SEARCH_INDEX = "policy-index"

python .\bridge_from_lab1.py --file .\data\sample-policy.txt --source sample-policy.txt
```

---

## 7) Optional impressive class demo
Follow:
- `docs/DEMO_SCRIPT.md`

Quick path:
```powershell
python .\scripts\demo\generate_dataset.py --out .\docs\samples\generated --count 60
$env:LAB1_URL = "https://$APP.azurewebsites.net"
$env:SEARCH_ENDPOINT = az keyvault secret show --vault-name $KV -n search-endpoint --query value -o tsv
$env:SEARCH_ADMIN_KEY = az keyvault secret show --vault-name $KV -n search-admin-key --query value -o tsv
python .\scripts\demo\run_pipeline.py --data .\docs\samples\generated

cd .\apps\demo-console
pip install -r requirements.txt
streamlit run app.py
```

---

## Troubleshooting quick hits
- `AuthorizationFailed roleAssignments/write`: use Step 4.4B fallback and continue.
- `Missing SEARCH_API_KEY`: set `$env:SEARCH_API_KEY = $env:SEARCH_ADMIN_KEY`.
- Bulk upload shows `doc_type: unknown` for all files: set `LAB1_URL` in Lab2 app settings so upload calls Lab1 intake.
- PowerShell `-H` / `-d @index.json` errors: wrong shell syntax; use `Invoke-RestMethod`.
- "Hey, Python developers" page: startup command missing; set startup file and restart app.
