# Theory Guide — Azure AI One-Day Workshop

Use this as companion reading for the labs. It is optimized for practical understanding in one day.

## 1) Why this architecture
You are building two real patterns used in enterprise teams:
- **Lab 1 (Intake Assistant):** unstructured docs → structured JSON decisions
- **Lab 2 (RAG Policy Bot):** grounded question-answering over internal documents

These map directly to common business workflows (ops intake, compliance, support, internal copilots).

## 2) Core design principles
- **Thin slice first:** make a minimal working flow before optimization
- **Grounding over guessing:** retrieved context + citations beats pure generation
- **Security by default:** secrets in Key Vault, identity via managed identity
- **Cost awareness:** constrain SKUs, chunk sizes, and token budgets

## 3) Identity, secrets, and trust boundaries
- **Managed Identity (MI):** app authenticates to Azure services without embedding credentials
- **Key Vault:** central secret store; App Service consumes via Key Vault references
- **Least privilege:** runtime app uses minimal permissions; ingestion/admin permissions are separate

Why it matters: this is one of the most transferable production skills from this workshop.

## 4) Prompting patterns used in class
### Structured extraction (Lab 1)
You force predictable JSON output with schema-like instructions.
Benefits:
- easier downstream automation
- reduced ambiguity
- easier validation and retries

### Grounded answering (Lab 2)
System behavior:
- answer from retrieved chunks only
- include citations (`[source#chunk]`)
- return “I don’t know” when confidence/context is insufficient

This improves trust and auditability.

## 5) RAG mechanics (quick mental model)
1. Split docs into chunks
2. Convert chunks to vectors (embeddings)
3. Store vectors + metadata in Azure AI Search
4. At query time: retrieve top-k relevant chunks
5. Generate answer constrained by those chunks

Tuning knobs:
- chunk size/overlap
- top-k retrieval
- answer style and refusal rules

## 6) Prompt injection and safety
Malicious text inside retrieved documents can try to override behavior.
Defenses in this course:
- strong system instructions
- retrieval-bound answering
- explicit refusal behavior
- no secrets in model prompts

## 7) Cost model (simple)
Main cost drivers:
- model token usage (prompt + output)
- search service tier/runtime
- app service uptime/size

Practical controls:
- short prompts, concise outputs
- smaller top-k by default
- clean up resources after class (`expiresAt` + cleanup script)

## 8) What “production-ready next” looks like
- evaluation harness for factuality/citations
- monitoring with safe logging/redaction
- stronger auth and RBAC segmentation
- CI/CD and environment promotion (dev → test → prod)

## 9) Suggested discussion prompts
- Where should humans stay in the loop?
- What should happen when retrieval confidence is low?
- How would you prove compliance for a regulator/customer?
- Which parts should be shared platform vs per-team customization?

## 10) Command-to-concept mapping (for teaching)
Use this to avoid "just copy/paste" feeling:
- `az keyvault secret set ...` → **secret lifecycle management**
- `az webapp config appsettings set ...` → **runtime secret injection**
- `az webapp up ...` → **deployment mechanics (build + release)**
- `python ingest.py` → **data preparation for retrieval quality**
- `POST /intake` / `POST /chat` → **behavior validation checkpoints**
