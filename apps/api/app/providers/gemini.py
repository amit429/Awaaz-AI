"""Gemini adapter implementing the Llm interface: JSON out, validated by the caller."""

import json
from typing import Any

import httpx

from app.providers.http import shared

from app.config import Settings

API = "https://generativelanguage.googleapis.com/v1beta/models"


_UNSUPPORTED = {"$schema", "$id", "additionalProperties", "maxLength", "minLength"}


def to_gemini_schema(node: Any) -> Any:
    """Gemini accepts a subset of JSON Schema: drop the keywords it rejects, turn
    {"type": ["string", "null"]} into a nullable string."""
    if isinstance(node, list):
        return [to_gemini_schema(n) for n in node]
    if not isinstance(node, dict):
        return node
    out = {k: to_gemini_schema(v) for k, v in node.items() if k not in _UNSUPPORTED}
    if "enum" in out and "type" not in out:
        out["type"] = "string"
    kind = out.get("type")
    if isinstance(kind, list):
        non_null = [k for k in kind if k != "null"]
        out["type"] = non_null[0] if non_null else "string"
        out["nullable"] = "null" in kind
    return out


class GeminiLlm:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def complete_json(self, prompt: str, *, schema: dict[str, Any]) -> dict[str, Any]:
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 900,
                "responseMimeType": "application/json",
                "responseSchema": to_gemini_schema(schema),
            },
        }
        url = f"{API}/{self.settings.llm_model}:generateContent?key={self.settings.llm_api_key}"
        client = shared("gemini", 20)
        r = await client.post(url, json=body)
        r.raise_for_status()
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)
