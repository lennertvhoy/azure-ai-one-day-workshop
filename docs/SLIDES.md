# Azure AI One-Day Workshop — Slides (Markdown)

## Slide 1 — Title
- Building Azure AI Apps in One Day
- Labs: Intake Assistant + RAG Policy Bot
- Outcome: ship practical, secure patterns you can reuse

**Image suggestion:** clean architecture banner (Azure icons: App Service, Key Vault, OpenAI, AI Search).

---

## Slide 2 — Learning outcomes
By end of day, participants can:
- Build document-to-JSON intake flows
- Build RAG bot with citations
- Deploy to Azure Web App with MI + Key Vault
- Explain core safety and cost controls

**Image suggestion:** checklist graphic with 4 outcomes.

---

## Slide 3 — Why these two labs
- Lab 1: operational automation from messy inputs
- Lab 2: trustworthy Q&A over internal knowledge
- Together: high-value enterprise AI baseline

**Screenshot suggestion:** side-by-side example outputs (JSON extraction + cited answer).

---

## Slide 4 — Delivery model (important)
- **Class mode:** instructor pre-provisions critical dependencies
- **Self-serve mode:** full setup docs remain for later reuse
- Goal: maximize learning, minimize setup drag

Teaching balance rule:
- Explain **why** (60–90 sec)
- Show **one command block** (copy/paste)
- Immediately validate with **one checkpoint**

**Image suggestion:** two-lane diagram (Class Mode vs Self-Serve Mode).

---

## Slide 5 — Architecture overview
- Client/UI → FastAPI app
- App uses Azure OpenAI
- Secrets from Key Vault
- (Lab 2) retrieval from Azure AI Search

**Image suggestion:** architecture diagram with trust boundaries.

---

## Slide 6 — Identity and secrets
- Managed Identity > static keys
- Key Vault references in app settings
- Least privilege role assignments

**Screenshot suggestion:** Web App identity + Key Vault role assignment page.

---

## Slide 7 — Lab 1 flow: Document → JSON
1) extract text
2) normalize with LLM
3) return strict JSON
4) route by team/priority

Command card (show, then run):
```powershell
az webapp config appsettings set ...
az webapp up ...
```

Talk track (max 90s):
- Why Key Vault refs: no secrets in code
- Why strict JSON: stable automation downstream

**Screenshot suggestion:** L1-S03 (`POST /intake` valid JSON response).

---

## Slide 8 — Structured prompting
- enforce output contract
- validate fields
- stable downstream automation

**Image suggestion:** mini JSON schema callout.

---

## Slide 9 — Lab 2 flow: RAG with citations
1) chunk docs
2) embed + index
3) retrieve top-k
4) answer with `[source#chunk]`

Command card (show, then run):
```bash
python ingest.py
curl .../chat
```

Talk track (max 90s):
- Why citations: trust + auditability
- Why "I don't know": safer than hallucination

**Screenshot suggestion:** L2-S04 cited answer example.

---

## Slide 10 — Prompt injection demo
- Malicious text can appear in source docs
- Retrieval does not remove risk by itself
- Defend with system constraints + refusal behavior

**Screenshot suggestion:** L2-S06 safe refusal response.

---

## Slide 11 — Cost controls
- small SKUs for labs
- short prompts / controlled top-k
- per-participant env tags + expiry
- cleanup automation

**Image suggestion:** cost dashboard screenshot or budget alert mockup.

---

## Slide 12 — IaC operations for paid courses
- one participant = one isolated RG
- scripted deploy + scripted cleanup
- repeatable setup for each cohort

**Screenshot suggestion:** terminal run of `infra/iac/deploy.ps1` + created RG list.

---

## Slide 13 — Common failure recovery
- missing Azure OpenAI access
- region/service quota constraints
- missing CLI paths on fresh VMs
- fallback paths ready

**Image suggestion:** troubleshooting decision tree.

---

## Slide 14 — What to build next
- eval harness and quality gates
- monitoring + redaction
- CI/CD and environment promotion
- connectors (Teams/SharePoint)

**Image suggestion:** roadmap timeline.

---

## Slide 15 — Wrap-up
- You shipped two real Azure AI patterns
- You used secure defaults
- You now have reusable templates for production pilots

Retro prompt (2 minutes):
- Which command felt like "magic" until explained?
- Which architecture choice gave the most confidence?
- What would you reuse tomorrow at work?

**Screenshot suggestion:** class “wins” collage (deployed endpoint, cited answer, role assignment).
