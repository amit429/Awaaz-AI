"""Sarvam adapter (transliteration for now; streaming STT/TTS arrive with the relay session)."""

import re

from app.config import Settings
from app.providers.http import shared

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
    client = shared("sarvam", 15)
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
    client = shared("sarvam", 15)
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


async def transcribe(
    audio: bytes, content_type: str, settings: Settings, lang: str = "unknown"
) -> str:
    """Speech to text for the user's own voice (Saaras). Empty string when nothing was heard."""
    if settings.mock_providers or not settings.sarvam_api_key:
        return ""
    ext = "webm" if "webm" in content_type else "mp4" if "mp4" in content_type else "wav"
    client = shared("sarvam", 30)
    r = await client.post(
        f"{API}/speech-to-text",
        files={"file": (f"voice.{ext}", audio, content_type)},
        data={"model": "saaras:v3", "mode": "transcribe", "language_code": lang},
        headers={"api-subscription-key": settings.sarvam_api_key},
    )
    r.raise_for_status()
    return str(r.json().get("transcript", "")).strip()
