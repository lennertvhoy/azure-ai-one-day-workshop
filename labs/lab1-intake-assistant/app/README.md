# Lab 1 app scaffold (FastAPI)

## Local run
```bash
cd labs/lab1-intake-assistant
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export AZURE_OPENAI_ENDPOINT="https://<your-aoai>.openai.azure.com"
export AZURE_OPENAI_API_KEY="..."
export AZURE_OPENAI_DEPLOYMENT="<chat-deployment-name>"

uvicorn app.main:app --reload --port 8001
```

Test:
```bash
curl -s http://localhost:8001/health
curl -s http://localhost:8001/intake \
  -H 'content-type: application/json' \
  -d '{"text":"Invoice from Contoso, invoice number INV-1001, total EUR 2500 due in 14 days."}' | jq
```

## Azure Web App
- Deploy this FastAPI app.
- Configure App Settings via **Key Vault references** for the 3 `AZURE_OPENAI_*` variables.
