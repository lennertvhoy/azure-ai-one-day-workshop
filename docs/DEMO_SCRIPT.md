# Demo Script — AI Operations Desk (Impressive & Realistic)

## What this demo shows
- Lab 1 and Lab 2 are separate APIs
- They can be connected into an enterprise workflow:
  `Incoming docs -> AI intake -> indexed knowledge -> grounded chatbot`

## 1) Prepare richer dataset
```bash
python scripts/demo/generate_dataset.py --out docs/samples/generated --count 60
```

## 2) Run Lab1 -> Lab2 batch pipeline
Set env vars:
- `LAB1_URL`
- `SEARCH_ENDPOINT`
- `SEARCH_ADMIN_KEY`
- optional `SEARCH_INDEX=policy-index`

Then:
```bash
python scripts/demo/run_pipeline.py --data docs/samples/generated
```

Expected output includes `chunks_uploaded`.

## 3) Run GUI
```bash
cd apps/demo-console
pip install -r requirements.txt
streamlit run app.py
```

## 4) Live storyline (5–8 min)
1. Intake tab: paste incident text, run Lab1 intake, show routing JSON.
2. Policy Copilot tab: ask policy question and show citations.
3. Connected tab: show both API outcomes in one flow.
4. Explain enterprise value: deterministic intake + grounded Q&A + security patterns.

## Suggested wow questions
- "An employee clicked a suspicious link. What is the immediate policy action?"
- "What SLA applies to reporting phishing?"
- "Given this invoice text, where should this be routed and why?"
