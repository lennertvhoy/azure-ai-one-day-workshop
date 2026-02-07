# AGENT_STATUS — Azure AI One-Day Workshop

Project: /home/ff/Documents/Azure_AI_OneDay_Workshop
Goal: Build a 1-day (09:00–17:00) Azure AI workshop package (Belgian professionals) with 2 end-to-end labs.
Current step: Generate day plan + lab manuals (Lab 1 Intake Assistant, Lab 2 RAG Policy Bot) aligned to GDPR-safe constraints.
Next step: Review with Lenny, then add starter repo scaffolds and a dry-run checklist.

## Decisions
- Stack: Python
- LLM: Azure OpenAI
- Vector store: Azure AI Search
- Secrets: Azure Key Vault (Managed Identity in Azure Web App)
- Constraints: GDPR-safe (no PII), sample data only

## Open Loops
- Confirm Azure region(s) to use (West Europe recommended).
- Confirm whether Document Intelligence is available in provided subscriptions/region.
- Decide whether to use App Service (Web App) vs Container Apps (kept to Web App per contract).

## Latest Update
- 2026-02-07: Project initialized; generating workshop docs + lab instructions.
