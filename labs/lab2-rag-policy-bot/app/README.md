# Lab 2 app scaffold (FastAPI + Azure AI Search)

## Local run (after indexing)
```bash
cd labs/lab2-rag-policy-bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Azure OpenAI
export AZURE_OPENAI_ENDPOINT="https://<your-aoai>.openai.azure.com"
export AZURE_OPENAI_API_KEY="..."
export AZURE_OPENAI_DEPLOYMENT="<chat-deployment-name>"

# Azure AI Search
export SEARCH_ENDPOINT="https://<your-search>.search.windows.net"
export SEARCH_ADMIN_KEY="..."   # ingestion only
export SEARCH_API_KEY="..."     # runtime query key (preferred)
export SEARCH_INDEX="policy-index"

# 1) Create index (once)
# curl -X PUT "$SEARCH_ENDPOINT/indexes/policy-index?api-version=2023-11-01" \
#   -H "Content-Type: application/json" -H "api-key: $SEARCH_ADMIN_KEY" \
#   -d @index.json

# 2) Ingest sample docs
python ingest.py --data ./data --index policy-index

# 3) Run API
uvicorn app.main:app --reload --port 8002
```

Test:
```bash
curl -s http://localhost:8002/chat \
  -H 'content-type: application/json' \
  -d '{"question":"When should I report phishing?"}' | jq
```

## Azure Web App
- Same pattern as Lab 1: Managed Identity + Key Vault references.
- Put Search keys and AOAI settings in Key Vault.
