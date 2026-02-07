"""Minimal ingestion script for Azure AI Search.

For workshop speed, this script uses SEARCH_ADMIN_KEY and uploads text chunks.
Vector embeddings are a stretch goal (requires embeddings deployment + vector upload).

Usage:
  python ingest.py --data ./data --index policy-index

Env:
  SEARCH_ENDPOINT
  SEARCH_ADMIN_KEY
"""

import argparse
import os
import uuid
from pathlib import Path

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient


def get_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing environment variable: {name}")
    return v


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> list[str]:
    # Char-based chunking for simplicity; swap to token-based (tiktoken) later.
    text = text.strip()
    if not text:
        return []
    out = []
    i = 0
    while i < len(text):
        out.append(text[i : i + chunk_size])
        i += chunk_size - overlap
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="Folder with .txt docs")
    ap.add_argument("--index", default="policy-index")
    args = ap.parse_args()

    endpoint = get_env("SEARCH_ENDPOINT")
    admin_key = get_env("SEARCH_ADMIN_KEY")

    client = SearchClient(endpoint=endpoint, index_name=args.index, credential=AzureKeyCredential(admin_key))

    data_dir = Path(args.data)
    paths = list(data_dir.glob("**/*.txt"))
    if not paths:
        raise SystemExit(f"No .txt files found in {data_dir}")

    batch = []
    for p in paths:
        text = p.read_text(encoding="utf-8", errors="ignore")
        chunks = chunk_text(text)
        for idx, ch in enumerate(chunks):
            batch.append(
                {
                    "id": str(uuid.uuid4()),
                    "content": ch,
                    "source": p.name,
                    "title": p.stem,
                    "chunk": idx,
                }
            )

    # Upload in small batches
    for i in range(0, len(batch), 500):
        client.upload_documents(documents=batch[i : i + 500])

    print(f"Uploaded {len(batch)} chunks to index {args.index}.")


if __name__ == "__main__":
    main()
