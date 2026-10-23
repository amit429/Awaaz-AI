"""Gemini adapter implementing the Llm interface: JSON out, validated by the caller."""

import json
from typing import Any

import httpx

from app.config import Settings

API = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiLlm:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def complete_json(self, prompt: str, *, schema: dict[str, Any]) -> dict[str, Any]:
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 300,
                "responseMimeType": "application/json",
                "responseSchema": schema,
            },
        }
        url = f"{API}/{self.settings.llm_model}:generateContent?key={self.settings.llm_api_key}"
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, json=body)
            r.raise_for_status()
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)
