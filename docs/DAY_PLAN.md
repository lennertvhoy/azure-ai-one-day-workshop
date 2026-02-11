# Day Plan — Azure AI One-Day Workshop (09:00–17:00)

## Title
**Building Azure AI Apps in One Day (Python): Document Intake + RAG Knowledge Bot**

## Target outcomes (by 17:00)
Participants can:
- Provision core Azure AI resources in a GDPR-safe way
- Build and deploy a **Python Azure Web App** that:
  1) extracts/normalizes data from documents and produces structured JSON
  2) answers questions over internal docs using **RAG with Azure AI Search** and citations
- Use **Key Vault + Managed Identity** correctly
- Understand baseline security/cost/operations decisions

---

## 09:00–09:30 — Kickoff + setup
- Objectives, expectations, “what you ship today”
- GDPR-safe rules: no PII, sample docs only
- Fresh VM bootstrap flow (participants do this themselves):
  - Install Git with winget
  - Clone repo
  - Run `scripts/setup/setup-all.ps1` and choose **Windows native**
  - Run verify step
- Prereqs checklist:
  - Azure subscription access + permission to create resources
  - Azure CLI installed + logged in
  - Python 3.11+, Git
- Repo overview (what folders are for)

**Checkpoint:** everyone can run `az account show` and has a resource group ready.

## 09:30–10:15 — Azure foundations (fast but correct)
- Resource group + region (recommend **West Europe**)
- Identities:
  - Why **Managed Identity** for Web App
  - Why Key Vault (secrets, rotation)
- Quick cost sanity (what costs money today)

**Checkpoint:** RG created; naming conventions agreed.

## 10:15–12:15 — Lab 1 build (Intake Assistant)
- Build a simple Streamlit (local) UI first for speed
- Implement:
  - Document extraction (Document Intelligence or OCR fallback)
  - Azure OpenAI enrichment → JSON output
  - Save results to storage + export

**Checkpoint (11:15):** pipeline produces valid JSON for at least 2 sample docs.

## 12:15–13:00 — Lunch

## 13:00–13:45 — Deploy Lab 1 to Azure Web App (enterprise auth)
- Create Web App
- Enable System-Assigned Managed Identity
- Create Key Vault + assign access
- Configure app settings (no secrets in code)

**Checkpoint:** deployed endpoint works; secrets are pulled from Key Vault.

## 13:45–15:45 — Lab 2 build (RAG Policy Bot)
- Ingestion pipeline:
  - chunking + metadata
  - embeddings
  - index into Azure AI Search
- Chat endpoint:
  - retrieve top-k
  - answer with citations + “I don’t know” behavior
  - prompt injection demo (bad doc content)

**Checkpoint (15:00):** bot answers 5 test questions with citations.

## 15:45–16:30 — Hardening: Safety, cost, ops
- Prompt injection patterns + mitigations
- Content filtering + safe logging
- Token budgets + caching options
- Basic evaluation harness

## 16:30–17:00 — Wrap + take-home template
- Architecture recap
- What to copy/paste into real projects
- Q&A
- Next steps: adding Teams/SharePoint connectors (conceptual)

---

## Materials to prepare (trainer)
- Sample documents pack (GDPR-safe): policies, SOPs, fake invoices, incident reports
- A slide deck (optional) with:
  - Architecture diagrams
  - Identity/Key Vault patterns
  - Responsible AI checklist
