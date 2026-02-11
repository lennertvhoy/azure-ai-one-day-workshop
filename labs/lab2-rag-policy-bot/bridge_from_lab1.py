"""Bridge script: Lab 1 intake API -> Lab 2 Search index.

Purpose:
- Call Lab 1 /intake to classify/normalize raw document text
- Chunk original text
- Upload chunks + intake metadata to Azure AI Search (policy-index)

Usage (PowerShell example):
  python .\bridge_from_lab1.py --file .\data\sample-policy.txt --source sample-policy.txt

Required env vars:
  LAB1_URL           e.g. https://app-aiws-1831894484.azurewebsites.net
  SEARCH_ENDPOINT    e.g. https://<search>.search.windows.net
  SEARCH_ADMIN_KEY   admin key (index write)
Optional:
  SEARCH_INDEX       default: policy-index
"""

import argparse
import json
import os
import uuid
from pathlib import Path
from urllib import request

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient


def get_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing environment variable: {name}")
    return v


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> list[str]:
    text = text.strip()
    if not text:
        return []
    out: list[str] = []
    i = 0
    step = max(1, chunk_size - overlap)
    while i < len(text):
        out.append(text[i : i + chunk_size])
        i += step
    return out


def call_lab1_intake(base_url: str, text: str) -> dict:
    """Call Lab 1 API so we reuse the same classification/routing logic.

    This is the core of the enterprise bridge:
    raw document -> normalized metadata -> indexed knowledge.
    """
    url = f"{base_url.rstrip('/')}/intake"
    body = json.dumps({"text": text}).encode("utf-8")
    req = request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    with request.urlopen(req, timeout=60) as resp:
        payload = resp.read().decode("utf-8")
    return json.loads(payload)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="Path to input text file")
    ap.add_argument("--source", default=None, help="Source label stored in search docs")
    ap.add_argument("--index", default=os.getenv("SEARCH_INDEX", "policy-index"))
    args = ap.parse_args()

    input_path = Path(args.file)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    raw_text = input_path.read_text(encoding="utf-8", errors="ignore")
    if not raw_text.strip():
        raise SystemExit("Input file is empty")

    lab1_url = get_env("LAB1_URL")
    intake = call_lab1_intake(lab1_url, raw_text)

    endpoint = get_env("SEARCH_ENDPOINT")
    admin_key = get_env("SEARCH_ADMIN_KEY")
    source_name = args.source or input_path.name

    client = SearchClient(endpoint=endpoint, index_name=args.index, credential=AzureKeyCredential(admin_key))

    # Keep searchable content as chunks, but enrich each chunk with Lab1 metadata.
    chunks = chunk_text(raw_text)
    docs = []
    for idx, ch in enumerate(chunks):
        docs.append(
            {
                "id": str(uuid.uuid4()),
                "content": ch,
                "source": source_name,
                "title": intake.get("doc_type", "unknown"),  # e.g. invoice / incident_report
                "chunk": idx,
            }
        )

    # Batch upload keeps requests smaller and more reliable.
    for i in range(0, len(docs), 500):
        client.upload_documents(documents=docs[i : i + 500])

    print(
        json.dumps(
            {
                "ok": True,
                "source": source_name,
                "chunks_uploaded": len(docs),
                "intake": {
                    "doc_type": intake.get("doc_type"),
                    "routing": intake.get("routing"),
                    "summary": intake.get("summary"),
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
