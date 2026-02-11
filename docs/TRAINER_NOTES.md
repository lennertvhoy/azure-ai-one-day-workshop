# Trainer Notes — Azure AI One-Day Workshop

## Teaching stance
- Keep momentum: build **something working** every 45–60 minutes.
- Default to “thin slice” implementations; hardening only after demo works.
- When in doubt: **reduce Azure surface area** (fewer services).

## GDPR-safe guardrails (repeat often)
- No production data. No emails. No customer PDFs.
- Use provided sample pack only.
- Do not paste secrets into chat logs.

## Recovery plans (when things break)
### Azure OpenAI access delays
- Have a fallback explanation + pre-provisioned resource in your subscription.
- If participants lack access: pair them or run “shared endpoint” demo (trainer-hosted) and keep lab code local.

### Document Intelligence not available in region
- Use OCR fallback path (or skip to “LLM-only extraction from text”).

### Azure AI Search quota/region issues
- Reduce index size; use fewer docs.
- Provide a prebuilt index JSON export (trainer) for import.

## Time control knobs
- Lab 1 runs long → skip CSV export + keep only JSON output.
- Lab 2 runs long → skip embeddings deep-dive; provide pre-chunked docs.

## Teaching cadence (balanced depth)
Use this loop per major step:
1. **Why (60–90 sec):** what problem this step solves.
2. **Do (2–5 min):** one copy/paste command block only.
3. **Check (30 sec):** one visible checkpoint (`/docs`, role assignment, citation output).
4. **Reflect (30 sec):** one sentence on production relevance.

Avoid multi-command walls without context; chunk commands into "command cards".

## Suggested checkpoints (verbatim)
- “Show me your endpoint response JSON.”
- “Show me Key Vault access policy / role assignment.”
- “Prove your app runs with **no secrets** in code.”
- “Ask a question; show citations; then ask a question that should return ‘I don’t know’.”

## Security talking points
- Managed Identity > keys
- Key Vault references in App Service settings
- Least privilege: search query vs index admin keys
- Logging: scrub prompts and docs

## Cost talking points
- AI Search pricing tiers
- OpenAI token costs: prompt length dominates
- Chunk size and top-k tuning

## Optional (M365 tie-in)
- Explain how these backends connect to:
  - SharePoint (docs)
  - Teams bot
  - Outlook triage
(Keep it conceptual unless you add Graph labs later.)
