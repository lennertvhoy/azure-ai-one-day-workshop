# Command Cards (Live Class)

Use these in class to keep pace: short command + short meaning + checkpoint.

## Card 1 — Login & context
```powershell
az login
az account show
```
Meaning: authenticate and verify tenant/subscription context.
Checkpoint: subscription shown is expected one.

## Card 2 — Key Vault reference wiring
```powershell
az webapp config appsettings set -g $RG -n $APP --settings ...
```
Meaning: app reads secrets from Key Vault at runtime.
Checkpoint: Web App Configuration shows `@Microsoft.KeyVault(...)` values.

## Card 3 — Deploy app code
```powershell
az webapp up -g $RG -n $APP -l $LOCATION --runtime "PYTHON:3.11"
```
Meaning: build + package + release code to existing Web App.
Checkpoint: `/docs` endpoint loads.

## Card 4 — Validate behavior
```text
POST /intake
```
Meaning: verify end-to-end extraction + normalization contract.
Checkpoint: JSON output includes doc_type/entities/summary/routing.

## Card 5 — RAG ingestion
```bash
python ingest.py
```
Meaning: transform docs into searchable vector chunks.
Checkpoint: expected chunk count indexed.

## Card 6 — RAG grounding
```text
Ask question in /chat endpoint
```
Meaning: answer comes from retrieved docs, not guessing.
Checkpoint: citations included (`[source#chunk]`) or safe refusal.
