# Done Definition Audit — Azure AI One-Day Workshop

Date: 2026-02-11
Scope: `azure-ai-one-day-workshop`
Audit model: **Build + Runtime + UI + Docs + Proof**

## Executive status

- **Overall:** 🟡 **Near-ready, not yet “Done”**
- **Why not done yet:** Cloud runtime/proof needs a clean re-run after intentional RG deletion; evidence bundle needs fresh screenshots/logs from the rebuilt environment.

---

## 1) Build checks

### Status: 🟢 Pass (local code integrity)

Evidence:
- `python -m compileall` succeeded for:
  - `labs/lab1-intake-assistant/app`
  - `labs/lab2-rag-policy-bot/app`
  - `labs/lab2-rag-policy-bot`
  - `scripts/demo`
- No compile failures.

Notes:
- One non-blocking warning in `bridge_from_lab1.py` docstring (PowerShell path escape sequence). Cosmetic, can be cleaned.

---

## 2) Runtime checks

### Status: 🟡 Previously pass, **needs fresh re-validation**

Known prior-good (from recent runs):
- Lab 1: `/health`, `/docs`, `POST /intake` working.
- Lab 2: `/health`, `/chat`, `/docs` working; startup command guidance added.

Current gap:
- Workshop RG/resources were intentionally deleted for clean reproducibility retest.
- Runtime proof is stale until redeploy + recheck is completed.

Required to close:
1. Recreate infra (clean path).
2. Redeploy Lab 1 + Lab 2.
3. Re-run endpoint checks and capture outputs.

---

## 3) UI checks

### Status: 🟢 Pass (feature completeness), 🟡 pending fresh cloud smoke

Evidence:
- Lab 2 app includes built-in web UI at `/` and bulk upload flow.
- Multi-file support added (`pdf/docx/txt/md/pptx`).

Gap:
- Need one fresh live smoke after rebuild to confirm UX from deployed URL.

---

## 4) Documentation checks

### Status: 🟢 Strong

Verified present:
- `docs/CLASS_FAST_PATH.md`
- `docs/COMMAND_CARDS.md`
- `docs/STUDENT_REPRO_PLAYBOOK.md`
- `docs/ACCESS_REQUIREMENTS.md`
- `docs/DEMO_SCRIPT.md`
- Windows-first setup and verify scripts
- Lab docs include troubleshooting and startup command guidance

Risk to monitor:
- Keep docs exactly aligned with any new runtime env key changes during next redeploy.

---

## 5) Proof package checks

### Status: 🟡 Partial

What exists:
- Historical run/verification context and substantial doc coverage.

Missing for “Done”:
- Fresh proof pack from the newly rebuilt environment:
  - endpoint curl/Invoke-RestMethod outputs
  - intake + upload/chat sample payload results
  - screenshots (key UI checkpoints)
  - final “student path from scratch” timing notes

---

## Red/Green summary

- ✅ Build: Green
- ⚠️ Runtime: Amber (rebuild proof needed)
- ✅ UI implementation: Green (pending redeploy smoke)
- ✅ Docs: Green
- ⚠️ Proof artifacts: Amber

**Decision:** Not final-done yet; one focused validation cycle should close it.

---

## Fast closure plan (tomorrow)

1. **Clean rebuild + env validation** (09:00 block)
2. **Lab 1 full check incl. `/intake`** (10:45 block)
3. **Lab 2 ingest + chat + UI check** (13:00 block)
4. **Windows-first student reproducibility pass** (14:45 block)
5. **Proof pack + final commit** (16:15 block)

If all five pass, project can be marked **Done** with confidence.
