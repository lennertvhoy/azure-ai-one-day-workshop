import json
import os
from typing import Any, Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()


def get_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing environment variable: {name}")
    return v


def get_aoai_client() -> AzureOpenAI:
    # For class speed we use API key auth (stored in Key Vault in Azure).
    # If your org supports Entra ID auth for Azure OpenAI, swap this for DefaultAzureCredential.
    endpoint = get_env("AZURE_OPENAI_ENDPOINT").strip().strip('"').strip("'")
    if not endpoint.startswith(("http://", "https://")):
        endpoint = f"https://{endpoint}"

    return AzureOpenAI(
        api_key=get_env("AZURE_OPENAI_API_KEY").strip(),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        azure_endpoint=endpoint,
    )


class IntakeRequest(BaseModel):
    text: str = Field(min_length=1, description="Extracted document text")


DocType = Literal["invoice", "incident_report", "policy", "unknown"]
Team = Literal["Finance", "IT", "HR", "Unknown"]
Priority = Literal["low", "medium", "high"]


class IntakeResponse(BaseModel):
    doc_type: DocType
    entities: dict[str, Any]
    summary: str
    routing: dict[str, Any]


SYSTEM_PROMPT = """
You are an assistant that normalizes messy office documents into strict JSON.
Rules:
- Output MUST be valid JSON and nothing else.
- Do not include markdown fences.
- If a field is unknown, use null or "unknown".
- Never invent personal data.

Return JSON with this schema:
{
  "doc_type": "invoice"|"incident_report"|"policy"|"unknown",
  "entities": { ... },
  "summary": "...",
  "routing": {"team": "Finance"|"IT"|"HR"|"Unknown", "priority": "low"|"medium"|"high"}
}
""".strip()


app = FastAPI(title="AI Intake Assistant", version="0.1.0")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/intake", response_model=IntakeResponse)
def intake(req: IntakeRequest):
    client = get_aoai_client()
    deployment = get_env("AZURE_OPENAI_DEPLOYMENT")

    resp = client.chat.completions.create(
        model=deployment,
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": req.text},
        ],
    )

    content = resp.choices[0].message.content or "{}"

    # Minimal robustness: try to parse JSON, otherwise return a structured error.
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Model did not return valid JSON: {e}\nRaw: {content[:500]}")

    return IntakeResponse.model_validate(parsed)
