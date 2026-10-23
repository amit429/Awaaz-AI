"""Turn what the user typed into what is spoken on the call.

Same language as the call (any spelling or script): converted to native script and spoken
without confirmation. Another language: translated and flagged `needs_confirm` (rule: translated
text is shown to the user and spoken only after they confirm).
"""

import asyncio
import re
from dataclasses import dataclass

from app.config import Settings
from app.providers import sarvam
from app.providers.base import Llm

_DEVANAGARI = re.compile(r"[ऀ-ॿ]")

LANGS = ["hindi_roman", "marathi_roman", "english", "other"]
DETECT_SCHEMA = {
    "type": "object",
    "properties": {"language": {"type": "string", "enum": LANGS}},
    "required": ["language"],
}
TRANSLATE_SCHEMA = {
    "type": "object",
    "properties": {"translation": {"type": "string"}},
    "required": ["translation"],
}

CALL_LANG_NAME = {"hi-IN": "Hindi", "mr-IN": "Marathi"}
SAME_LANG = {"hi-IN": "hindi_roman", "mr-IN": "marathi_roman"}


@dataclass
class Prepared:
    spoken: str
    needs_confirm: bool
    kind: str  # "as_is" | "same_language" | "translated"
    detected: str | None = None


def _detect_prompt(text: str) -> str:
    return (
        "Which language is this text typed in? hindi_roman (Hindi in English letters), "
        "marathi_roman (Marathi in English letters), english, or other.\n\nText: " + text
    )


def _translate_prompt(text: str, call_lang: str) -> str:
    name = CALL_LANG_NAME.get(call_lang, "Hindi")
    return (
        f"Translate this text faithfully into {name}, in its native script, to be spoken aloud on a "
        "phone call. Keep every number, name and medicine name exactly; do not add or remove "
        "information.\n\nText: " + text
    )


async def prepare_say(text: str, call_lang: str, settings: Settings, llm: Llm) -> Prepared:
    text = text.strip()
    if not text:
        return Prepared("", False, "as_is")
    if _DEVANAGARI.search(text) and not sarvam.needs_transliteration(text):
        return Prepared(text, False, "as_is")  # already native script
    if not sarvam.needs_transliteration(text):  # digits and punctuation only
        return Prepared(text, False, "as_is")
    # Latin letters: detect the language and transliterate in parallel.
    translit, detected = await asyncio.gather(
        sarvam.transliterate(text, settings, target=call_lang),
        llm.complete_json(_detect_prompt(text), schema=DETECT_SCHEMA),
        return_exceptions=True,
    )
    translit_ok = not isinstance(translit, BaseException)
    if isinstance(detected, BaseException) or "language" not in detected:
        # Cannot tell: show the transliteration and ask.
        return Prepared(translit if translit_ok else text, True, "same_language", None)
    language = detected["language"]
    if language == SAME_LANG.get(call_lang) and translit_ok:
        return Prepared(translit, False, "same_language", language)
    try:
        out = await llm.complete_json(_translate_prompt(text, call_lang), schema=TRANSLATE_SCHEMA)
        return Prepared(out["translation"], True, "translated", language)
    except Exception:  # noqa: BLE001 - provider failure must not speak anything unreviewed
        return Prepared(translit if translit_ok else text, True, "same_language", language)
