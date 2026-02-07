import os
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field
from openai import AzureOpenAI

from .search import search_top_k


def get_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing environment variable: {name}")
    return v


def get_aoai_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=get_env("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        azure_endpoint=get_env("AZURE_OPENAI_ENDPOINT"),
    )


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)


class Citation(BaseModel):
    source: str
    chunk: int | None = None


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    debug: dict[str, Any] | None = None


SYSTEM_PROMPT = """
You are a policy assistant.
Rules:
- Answer ONLY using the provided SOURCES.
- If the sources do not contain the answer, say: "I don't know based on the provided documents."
- Provide citations in the response as [source#chunk].
""".strip()


app = FastAPI(title="RAG Policy Bot", version="0.1.0")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    index_name = os.getenv("SEARCH_INDEX", "policy-index")
    top_k = int(os.getenv("SEARCH_TOP_K", "5"))

    hits = search_top_k(index_name=index_name, query=req.question, top=top_k)

    # Build source context.
    sources_lines: list[str] = []
    citations: list[Citation] = []

    for h in hits:
        src = str(h.get("source") or "unknown")
        chunk = h.get("chunk")
        content = str(h.get("content") or "")
        citations.append(Citation(source=src, chunk=chunk if isinstance(chunk, int) else None))
        sources_lines.append(f"SOURCE: {src}#${chunk}\n{content}")

    sources_block = "\n\n".join(sources_lines)

    client = get_aoai_client()
    deployment = get_env("AZURE_OPENAI_DEPLOYMENT")

    user_prompt = f"QUESTION:\n{req.question}\n\nSOURCES:\n{sources_block}"

    resp = client.chat.completions.create(
        model=deployment,
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    answer = (resp.choices[0].message.content or "").strip()

    return ChatResponse(
        answer=answer,
        citations=citations,
        debug={"hits": len(hits)},
    )
