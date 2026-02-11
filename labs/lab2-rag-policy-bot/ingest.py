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
    """Read required env var or stop with clear error.

    Why: students should fail fast when setup is incomplete.
    """
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
    # CLI arguments keep the script reusable across classes/environments.
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="Folder with .txt docs")
    ap.add_argument("--index", default="policy-index")
    args = ap.parse_args()

    # These come from your shell session (usually loaded from Key Vault).
    endpoint = get_env("SEARCH_ENDPOINT")
    admin_key = get_env("SEARCH_ADMIN_KEY")

    # SearchClient writes into one specific index.
    client = SearchClient(endpoint=endpoint, index_name=args.index, credential=AzureKeyCredential(admin_key))

    data_dir = Path(args.data)
    paths = list(data_dir.glob("**/*.txt"))
    if not paths:
        raise SystemExit(f"No .txt files found in {data_dir}")

    # Build one flat list of index documents.
    # Each chunk becomes one searchable document.
    batch = []
    for p in paths:
        text = p.read_text(encoding="utf-8", errors="ignore")
        chunks = chunk_text(text)
        for idx, ch in enumerate(chunks):
            batch.append(
                {
                    "id": str(uuid.uuid4()),  # unique key required by Search index
                    "content": ch,            # searchable text
                    "source": p.name,         # filename for citations
                    "title": p.stem,          # lightweight label
                    "chunk": idx,             # chunk number for [source#chunk]
                }
            )

    # Upload in chunks of 500 docs to avoid oversized requests.
    for i in range(0, len(batch), 500):
        client.upload_documents(documents=batch[i : i + 500])

    print(f"Uploaded {len(batch)} chunks to index {args.index}.")


if __name__ == "__main__":
    main()
