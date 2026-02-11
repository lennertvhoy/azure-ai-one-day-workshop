import os
from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient


def get_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing environment variable: {name}")
    return v


def get_search_client(index_name: str) -> SearchClient:
    endpoint = get_env("SEARCH_ENDPOINT")
    # Prefer query key for runtime; allow admin key fallback for workshop/dev speed.
    key = os.getenv("SEARCH_API_KEY") or os.getenv("SEARCH_ADMIN_KEY")
    if not key:
        raise RuntimeError("Missing environment variable: SEARCH_API_KEY (or SEARCH_ADMIN_KEY fallback)")
    return SearchClient(endpoint=endpoint, index_name=index_name, credential=AzureKeyCredential(key))


def search_top_k(index_name: str, query: str, top: int = 5, min_score: float = 0.0) -> list[dict[str, Any]]:
    """Retrieve top documents and optionally filter weak matches by score."""
    client = get_search_client(index_name)
    results = client.search(search_text=query, top=top, query_type="simple")
    hits: list[dict[str, Any]] = []
    for r in results:
        row = dict(r)
        score = float(row.get("@search.score", 0.0) or 0.0)
        if score >= min_score:
            hits.append(row)
    return hits


def upload_documents(index_name: str, documents: list[dict[str, Any]]) -> None:
    endpoint = get_env("SEARCH_ENDPOINT")
    key = os.getenv("SEARCH_ADMIN_KEY") or os.getenv("SEARCH_API_KEY")
    if not key:
        raise RuntimeError("Missing SEARCH_ADMIN_KEY (or SEARCH_API_KEY fallback) for indexing")

    client = SearchClient(endpoint=endpoint, index_name=index_name, credential=AzureKeyCredential(key))
    for i in range(0, len(documents), 500):
        client.upload_documents(documents=documents[i : i + 500])
