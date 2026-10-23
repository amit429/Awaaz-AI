"""Sarvam adapter (transliteration for now; streaming STT/TTS arrive with the relay session)."""

import re

import httpx

from app.config import Settings

API = "https://api.sarvam.ai"
_LATIN = re.compile(r"[A-Za-z]")


def needs_transliteration(text: str) -> bool:
    """True when the text has Latin letters (romanised Hindi or English)."""
    return bool(_LATIN.search(text))


async def transliterate(
    text: str, settings: Settings, target: str = "hi-IN", source: str = "en-IN"
) -> str:
    """Romanised text to native script, numbers in spoken form ('Telma 40' to 'टेल्मा चालीस').

    Returns the text unchanged in mock mode, when no key is set, or when it is already native.
    """
    if settings.mock_providers or not settings.sarvam_api_key:
        return text
    if source == "en-IN" and not needs_transliteration(text):
        return text
    body = {
        "input": text,
        "source_language_code": source,
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


async def translate(text: str, settings: Settings, target: str, source: str = "hi-IN") -> str:
    """Translate a caption. Meaning can drift on names and medicines: always keep the original."""
    if settings.mock_providers or not settings.sarvam_api_key:
        return text
    body = {
        "input": text,
        "source_language_code": source,
        "target_language_code": target,
        "model": "sarvam-translate:v1",
        "numerals_format": "international",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"{API}/translate", json=body, headers={"api-subscription-key": settings.sarvam_api_key}
        )
        r.raise_for_status()
        return r.json()["translated_text"]


READ_MODES = {"original", "hinglish", "english", "marathi"}


async def for_reading(text: str, mode: str, settings: Settings, source: str = "hi-IN") -> str:
    """The caption in the user's reading mode. original and hinglish are faithful word for word."""
    if mode == "hinglish":
        return await transliterate(text, settings, target="en-IN", source=source)
    if mode == "english":
        return await translate(text, settings, target="en-IN", source=source)
    if mode == "marathi":
        return await translate(text, settings, target="mr-IN", source=source)
    return text
