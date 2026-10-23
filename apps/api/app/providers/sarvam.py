"""Sarvam adapter (transliteration for now; streaming STT/TTS arrive with the relay session)."""

import re

import httpx

from app.config import Settings

API = "https://api.sarvam.ai"
_LATIN = re.compile(r"[A-Za-z]")


def needs_transliteration(text: str) -> bool:
    """True when the text has Latin letters (romanised Hindi or English)."""
    return bool(_LATIN.search(text))


async def transliterate(text: str, settings: Settings, target: str = "hi-IN") -> str:
    """Romanised text to native script, numbers in spoken form ('Telma 40' to 'टेल्मा चालीस').

    Returns the text unchanged in mock mode, when no key is set, or when it is already native.
    """
    if settings.mock_providers or not settings.sarvam_api_key or not needs_transliteration(text):
        return text
    body = {
        "input": text,
        "source_language_code": "en-IN",
        "target_language_code": target,
        "numerals_format": "native",
        "spoken_form": True,
        "spoken_form_numerals_language": "native",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"{API}/transliterate",
            json=body,
            headers={"api-subscription-key": settings.sarvam_api_key},
        )
        r.raise_for_status()
        return r.json()["transliterated_text"]
