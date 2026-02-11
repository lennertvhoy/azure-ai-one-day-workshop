# Sample Document Pack

GDPR-safe sample inputs for workshop labs.

## Contents
- `invoice-001.md`, `invoice-002.md`
- `incident-report-001.md`, `incident-report-002.md`
- `policy-security.md`, `policy-privacy.md`

## Build PDFs
Prereqs:
- `pandoc`
- `tectonic`
- `mmdc` (mermaid-cli)

Run:
```bash
cd docs/samples
./build.sh
```

Output:
- `docs/samples/pdf_output/*.pdf`

## Usage in class
- Lab 1: paste text excerpts from these docs into `POST /intake` for quick validation.
- Lab 1 (optional Document Intelligence): upload generated PDFs.
- Lab 2: use policy/incident docs as ingestion material.
