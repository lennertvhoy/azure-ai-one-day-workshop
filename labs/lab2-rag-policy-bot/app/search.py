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
    key = get_env("SEARCH_API_KEY")  # use query key for runtime, admin key for ingestion
    return SearchClient(endpoint=endpoint, index_name=index_name, credential=AzureKeyCredential(key))


def search_top_k(index_name: str, query: str, top: int = 5) -> list[dict[str, Any]]:
    client = get_search_client(index_name)
    results = client.search(search_text=query, top=top, query_type="simple")
    hits: list[dict[str, Any]] = []
    for r in results:
        hits.append(dict(r))
    return hits
