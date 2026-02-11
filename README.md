# Azure AI — One Day Workshop (09:00–17:00)

Audience: Belgian technical professionals with **some Azure**.

## Package contents
- `docs/DAY_PLAN.md` — minute-by-minute schedule + learning objectives
- `docs/TRAINER_NOTES.md` — facilitation notes, checkpoints, recovery plans
- `labs/lab1-intake-assistant/LAB.md` — Lab 1 manual (Document → JSON → workflow)
- `labs/lab2-rag-policy-bot/LAB.md` — Lab 2 manual (RAG bot with citations)
- `infra/` — infra notes + az cli snippets

## Guardrails (GDPR-safe)
- Use **sample documents** only (no PII)
- Use **Key Vault** for secrets
- Prefer **Managed Identity** from Azure Web App
- Log safely (no prompts with secrets/PII)

## Setup scripts (Windows + WSL)
- Interactive launcher (choose Windows/WSL/verify):
  - `powershell -ExecutionPolicy Bypass -File .\scripts\setup\setup-all.ps1`
- Windows clean install:
  - `powershell -ExecutionPolicy Bypass -File .\scripts\setup\windows\install.ps1`
  - Verify: `powershell -ExecutionPolicy Bypass -File .\scripts\setup\windows\verify.ps1`
- WSL setup:
  - `bash scripts/setup/wsl/install_wsl.sh`
  - Verify: `bash scripts/setup/wsl/verify_wsl.sh`
