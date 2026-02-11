"""Batch pipeline: send docs through Lab1 intake, then index into Lab2 Search.

Usage:
  python scripts/demo/run_pipeline.py --data docs/samples/generated

Env:
  LAB1_URL
  SEARCH_ENDPOINT
  SEARCH_ADMIN_KEY
Optional:
  SEARCH_INDEX (default policy-index)
"""

from __future__ import annotations

import argparse
import json
import os
import uuid
from pathlib import Path
from urllib import request

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient


def env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing env: {name}")
    return v


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 120) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks = []
    step = max(1, chunk_size - overlap)
    i = 0
    while i < len(text):
        chunks.append(text[i : i + chunk_size])
        i += step
    return chunks


def call_intake(base_url: str, text: str) -> dict:
    """Send one document to Lab1 to get standardized metadata.

    Reusing Lab1 here guarantees the same logic in API + batch pipeline.
    """
    body = json.dumps({"text": text}).encode("utf-8")
    req = request.Request(f"{base_url.rstrip('/')}/intake", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    with request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--index", default=os.getenv("SEARCH_INDEX", "policy-index"))
    args = ap.parse_args()

    lab1 = env("LAB1_URL")
    endpoint = env("SEARCH_ENDPOINT")
    key = env("SEARCH_ADMIN_KEY")

    client = SearchClient(endpoint=endpoint, index_name=args.index, credential=AzureKeyCredential(key))

    data_dir = Path(args.data)
    files = sorted(data_dir.glob("*.txt"))
    if not files:
        raise SystemExit(f"No .txt files in {data_dir}")

    uploaded = 0
    for f in files:
        # 1) Read file text
        text = f.read_text(encoding="utf-8", errors="ignore")

        # 2) Normalize/classify via Lab1
        intake = call_intake(lab1, text)
        doc_type = intake.get("doc_type", "unknown")

        # 3) Chunk text and map into Search index documents
        docs = []
        for i, ch in enumerate(chunk_text(text)):
            docs.append(
                {
                    "id": str(uuid.uuid4()),
                    "content": ch,
                    "source": f.name,
                    "title": doc_type,
                    "chunk": i,
                }
            )

        # 4) Upload chunk-docs to Search so Lab2 can retrieve them
        if docs:
            client.upload_documents(documents=docs)
            uploaded += len(docs)

    print(json.dumps({"ok": True, "files": len(files), "chunks_uploaded": uploaded}, indent=2))


if __name__ == "__main__":
    main()
