"""Languages Awaaz supports, and caption translation into the user's reading language.

Spoken languages (what the other person speaks) map to Sarvam codes. Reading languages add
Hinglish (`hi-Latn`): Hindi written in English letters.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.config import Settings
from app.providers import sarvam
from app.providers.base import Llm

SPOKEN: dict[str, tuple[str, str]] = {  # code -> (English name, Sarvam code)
    "hi": ("Hindi", "hi-IN"),
    "en": ("English", "en-IN"),
    "mr": ("Marathi", "mr-IN"),
    "bn": ("Bengali", "bn-IN"),
    "ta": ("Tamil", "ta-IN"),
    "te": ("Telugu", "te-IN"),
    "kn": ("Kannada", "kn-IN"),
    "ml": ("Malayalam", "ml-IN"),
    "gu": ("Gujarati", "gu-IN"),
    "pa": ("Punjabi", "pa-IN"),
    "or": ("Odia", "od-IN"),
}
READING = [*SPOKEN, "hi-Latn"]
HINGLISH = "hi-Latn"
log = logging.getLogger("awaaz.languages")


def short(code: str) -> str:
    """'hi-IN' or 'hi' to 'hi'; 'od-IN' to 'or'."""
    base = code.split("-")[0].lower()
    return "or" if base == "od" else base


def call_code(lang: str | None) -> str:
    """A spoken language as the call language code ('hi' to 'hi-IN'); Hindi if unknown."""
    if not lang:
        return "hi-IN"
    return SPOKEN.get(short(lang), SPOKEN["hi"])[1]


def name_of(read_lang: str) -> str:
    if read_lang == HINGLISH:
        return "Hinglish (Hindi written in English letters)"
    return SPOKEN.get(read_lang, ("English", ""))[0]


def needs_translation(call_lang: str, read_lang: str) -> bool:
    return short(call_lang) != read_lang


SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"translation": {"type": "string"}},
    "required": ["translation"],
}

PROMPT = """You translate one sentence from a live phone call for a deaf reader.
It is {source} speech-recognition output and may contain mistakes, especially in medicine and brand names.
Contact notes (use them to resolve unclear words, never to add facts): {notes}
Write it in {target}. Keep every number, price, time and date exactly, as digits. Keep medicine and brand names as they are, in Latin letters. Do not add or remove information.

Sentence: {text}"""

Translator = Callable[[str, str, str, str], Awaitable[str | None]]


def make_translator(settings: Settings, llm: Llm) -> Translator:
    """Caption text into the reading language. Hindi to Hinglish is a transliteration (word for
    word); everything else goes through the LLM with call context, then Sarvam as a fallback."""

    async def translate(text: str, call_lang: str, read_lang: str, notes: str) -> str | None:
        if not needs_translation(call_lang, read_lang):
            return None
        if settings.mock_providers:
            return None
        if read_lang == HINGLISH and short(call_lang) == "hi":
            try:
                return await sarvam.transliterate(text, settings, target="en-IN", source="hi-IN")
            except Exception:  # noqa: BLE001 - captions still show the original
                return None
        prompt = PROMPT.format(
            source=SPOKEN.get(short(call_lang), ("Hindi", ""))[0],
            target=name_of(read_lang),
            notes=notes or "none",
            text=text,
        )
        try:
            out = await llm.complete_json(prompt, schema=SCHEMA)
            translated = str(out.get("translation", "")).strip()
            if translated:
                return translated
        except Exception:  # noqa: BLE001 - fall back to Sarvam
            log.warning("LLM caption translation failed; trying Sarvam")
        if read_lang in SPOKEN:
            try:
                return await sarvam.translate(
                    text, settings, target=SPOKEN[read_lang][1], source=call_code(call_lang)
                )
            except Exception:  # noqa: BLE001
                return None
        return None

    return translate
