# Demo Console (AI Operations Desk)

Simple GUI for class demos:
- Tab 1: call Lab 1 `/intake`
- Tab 2: call Lab 2 `/chat`
- Tab 3: show connected flow in one screen

## Run locally

```bash
cd apps/demo-console
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Optional env vars:
- `LAB1_URL` (default: deployed Lab 1 URL)
- `LAB2_URL` (default: deployed Lab 2 URL)

## Notes
This UI is intentionally lightweight for workshop speed and reliability.
